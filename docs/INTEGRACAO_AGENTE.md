# Respostas — integração Agente ↔ trivus-api (Plano 08)

> Todas as respostas abaixo são **request/response reais** executados contra a API
> (commit atual da `develop`), com tokens redigidos. Onde o comportamento vinha de
> código, o arquivo-fonte está citado.
>
> **⚠️ Descoberta durante a coleta:** o `PATCH /crm/leads/{id}/agendamento` (e os
> patches de comparecimento/fechamento) estouravam **500** — datas ISO string vs
> coluna `DATE` no asyncpg. **Corrigido + e2e de regressão** (commit `fix(crm):
> coercao de datas ISO->date...`). O agente precisa rodar contra build que
> contenha esse fix (branch `develop`).

## 🎯 Atalho (entregues junto deste doc)

1. **`docs/API_REFERENCE.md`** — no repo (endpoints, payloads, regras de negócio).
2. **`openapi.json`** — dump real do `GET /openapi.json` (arquivo anexo `TRIVUS_openapi.json`; regenere quando quiser nesse endpoint).
3. **Staging: ainda NÃO existe** (deploy Coolify pendente). Ambiente completo local em 2 comandos: ver `ONBOARDING.md` (repo trivus-api) — sobe db+api+web e o `scripts/seed_demo` popula lojas/funis/SDRs/leads. Os UUIDs mudam a cada re-seed, então **descubra o `store_id` via API** (abaixo) em vez de fixar.
4. **Lead real completo** (item do `GET /crm/leads`, com agendamento, comparecimento e venda):

```json
{"id": "29d737a0-78ea-4421-9b12-3a084cdeb8fe", "store_id": "11fc7e9a-ccec-4ceb-b4e1-4e821e473e67", "stage_id": "8ae8be40-74e3-48db-b206-10b52e870a72", "sort_order": 1, "assigned_to": "76492699-459d-4f41-bbbb-d1d7add7f906", "vendedor_id": "53b971d6-0ccf-4385-ab7b-104cc5e31023", "agendado_por": "76492699-459d-4f41-bbbb-d1d7add7f906", "campaign_id": "3d06a946-080e-46c4-8366-a2cc28b0ddf3", "funil": "receptivo", "qualificado": true, "origem_mkt": null, "urgencia_venda": "alta", "nome": "Bruno Rodrigues", "telefone": "(11) 93684-9133", "lid": null, "bairro": "Vila Nova", "cidade": "Caxias do Sul", "modelo": "Renegade", "veiculo": "Renegade 2021", "ano": "2021", "cor": "Prata", "combustivel": "Gasolina", "quilometragem": "103000", "transmissao": null, "valor_tabela_fipe": 164665.99, "tem_financiamento": true, "saldo_quitacao": null, "valor_pretendido": 83551.43, "valor_compra": 125478.79, "data_agendamento": "2026-07-07", "hora_agendamento": "17:00", "data_marcacao_agendamento": "2026-07-05", "compareceu_agendamento": true, "data_compareceu": "2026-07-08", "fechou_negocio": true, "data_fechou_negocio": "2026-07-15", "receita": 132847.98, "despesa": 110061.59, "rentabilidade": 22786.39, "observacoes": "Interesse em troca com entrada.", "created_at": "2026-07-02T15:00:00+00:00", "updated_at": "2026-07-02T15:00:00+00:00"}
```

---

## Bloco A — Autenticação e escopo

### A1. Login

```
POST /auth/login
REQ:  {"email": "carlos@trivus.local", "password": "demo123"}
→ 200: {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<redigido>",
        "user": {"id": "d73d2b0e-...", "email": "carlos@trivus.local", "name": "Carlos",
                 "role": "client", "parent_store_id": null}}
```

- Claims do JWT: `sub` (user id), `role`, `parent_store_id`, `exp`.
- **Expira em 7 dias** (`JWT_EXPIRES_MINUTES=10080`, configurável por env).
- **Não há refresh token.** Estratégia: re-login quando vier `401` (`{"error": "Token ausente"}` / inválido).

### A2. ⭐ Usuário de serviço "IA"

**Recomendação: um usuário `role=client` por loja.** Motivo (regra real de visibilidade,
`crm/infrastructure/repositories.py::list_for_board`): `shop_user` — **qualquer**
shop_role, até gerente — só enxerga leads com `assigned_to = ele mesmo`; `client`
e `admin` veem **todos** os leads da loja. O agente precisa achar lead por telefone,
então `shop_user` não serve. `client` faz tudo que o agente precisa (ler/criar/editar
lead, agendar, atribuir, ler agenda) e **não** acessa rotas `/admin/*` (403).

Criação (admin):

```
POST /admin/users            {"email": "ia@sualoja.com.br", "password": "...", "name": "Agente IA"}
PUT  /admin/users/{id}/stores {"store_ids": ["<store_id>"], "owner_store_ids": []}
```

- ⚠️ o e-mail passa por validação `EmailStr` — **TLD `.local` é recusado** (422). Use domínio real.
- O vínculo via `PUT .../stores` habilita o `GET /stores/mine` para o usuário (abaixo).
- **`menu_permissions` afeta SÓ o front** — nenhuma rota da API o consulta (verificado por grep).

### A3. Escopo por loja

- O token **não** restringe loja para `client`/`admin`; as rotas recebem **`store_id` em query** (`GET /crm/leads?store_id=...`, `GET /agenda?store_id=...`) ou o lead já carrega `store_id`.
- `shop_user` tem `parent_store_id` no token e a visibilidade por `assigned_to`.
- Como descobrir a loja do usuário de serviço: `GET /stores/mine` (novo, nesta develop) →
  `[{"id": "...", "nome_fantasia": "AutoStar — Matriz", "crm_enabled": true, "active": true}]`.
- ⚠️ **Honestidade:** hoje um `client` autenticado consegue passar `store_id` de outra loja
  nas rotas CRM (não há verificação de vínculo além do gate de feature). Endureceremos;
  o adapter deve sempre usar o `store_id` da própria loja.

### A4. ⭐ Gate de assinatura/feature

- Gates **existem só nas leituras**: `GET /crm/funnels` e `GET /crm/leads` (key `crm.kanban`), `GET /agenda` (key `agenda`). Criação/edição de lead **não** é gateada.
- Corpo exato (real, loja com assinatura suspensa):

```
GET /agenda?store_id=<loja_suspensa>
→ 403: {"error": "feature_locked", "feature_key": "agenda"}
```

- Não há feature key específica de IA. Regras: loja sem `company_id` = legado sem gate; `admin` nunca é gateado.

---

## Bloco B — Leads

### B1. Buscar por telefone

**Não existe busca por telefone.** `GET /crm/leads?store_id=...` devolve a **lista plana
completa** da loja (sem paginação — 130 itens no demo). O cliente filtra localmente.
As variantes do 9º dígito e `lid` **não** são tratadas nessa rota (esse matching é
interno do webhook Z-API) → normalize/gere variantes no adapter.

### B2. Criar lead

```
POST /crm/leads
REQ:  {"store_id": "11fc7e9a-...", "stage_id": "037ec391-...", "funil": "receptivo",
       "nome": "Teste Agente", "telefone": "(11) 91234-5678"}
→ 201: {"id": "dc8c3d63-...", "store_id": "11fc7e9a-...", "stage_id": "037ec391-...",
        "sort_order": 0, "assigned_to": null, ...todos os demais campos null...}
```

⭐ **`stage_id` é OBRIGATÓRIO** — a API **não** coloca na 1ª etapa sozinha e **não**
faz round-robin de SDR (isso existe só no webhook Z-API interno). O chamador resolve:

```
GET /crm/funnels?store_id=...
→ 200: [{"id": "...", "name": "Funil Padrão", "stages": [
   {"id": "037ec391-...", "name": "RECEBIDOS",   "sort_order": 0},
   {"id": "3dbe3bbc-...", "name": "CLASSIFICADOS","sort_order": 1},
   {"id": "b87b07a5-...", "name": "QUALIFICADOS", "sort_order": 2},
   {"id": "1fee1d4e-...", "name": "AGENDADOS",    "sort_order": 3},
   {"id": "8968b63b-...", "name": "EM ATENDIMENTO","sort_order": 4},
   {"id": "76eedc46-...", "name": "VEICULOS COMPRADOS", "sort_order": 5},
   {"id": "8ae8be40-...", "name": "VEICULOS VENDIDOS",  "sort_order": 6}]}]
```

Cachear o `stage_id` de RECEBIDOS por loja e mandar `assigned_to` se quiser atribuição.

### B3. ⭐ Dedupe

**Duplica.** POST com o mesmo telefone criou um 2º lead (comprovado: 2 leads com
`(11) 91234-5678` após duas chamadas). Dedupe é responsabilidade do chamador:
buscar antes (B1) e decidir atualizar × criar.

### B4. Atualizar qualificação

```
PATCH /crm/leads/{id}
REQ:  {"qualificado": true, "urgencia_venda": "alta",
       "observacoes": "[IA] Cliente quer SUV ate 120k", "origem_mkt": "whatsapp-ia"}
→ 200: lead completo atualizado
```

Campos aceitos (`UpdateLeadRequest`): `campaign_id, funil, nome, telefone, cidade,
modelo, ano, assigned_to, vendedor_id, observacoes, bairro, veiculo, cor, combustivel,
quilometragem, transmissao, lid, qualificado, origem_mkt, urgencia_venda,
tem_financiamento`. **Nenhum bloqueio por papel.**
⚠️ O handler usa `exclude_none` → **mandar `null` NÃO limpa o campo** (é descartado).
Não há como "zerar" um campo por esse PATCH.

---

## Bloco C — Agenda / agendamento

### C1. Marcar

```
PATCH /crm/leads/{id}/agendamento
REQ:  {"data_agendamento": "2026-07-20", "hora_agendamento": "14:30"}
→ 200: {..., "data_agendamento": "2026-07-20", "hora_agendamento": "14:30:00",
        "data_marcacao_agendamento": "2026-07-16", "agendado_por": "ac6cfdff-..."}
```

- Formatos: `data` = `YYYY-MM-DD`; `hora` = `HH:MM` (normalizada para `HH:MM:SS`) ou `HH:MM:SS`.
- O back **seta sozinho** `agendado_por` (usuário do token) e `data_marcacao_agendamento = hoje`, **apenas quando é agendamento novo**.

### C2. Cancelar — mesmo endpoint com nulls

```
REQ:  {"data_agendamento": null, "hora_agendamento": null}
→ 200: {..., "data_agendamento": null, "hora_agendamento": null, "agendado_por": null}
```

### C3. Reagendar

Mesmo endpoint com valores novos. Regra (`domain/lead_patch.py`):
`data_marcacao_agendamento` e `agendado_por` **permanecem os originais** (só são
recalculados se não havia agendamento). Não grava histórico (histórico é de etapa).

### C4. Agenda de um dia

```
GET /agenda?store_id=...&apply_to=agendamento&preset=custom&from=2026-07-16&to=2026-07-16&page=1&page_size=100
→ 200: {"items": [ <lead completo>, ... ], "total": N, "page": 1}
```

- Params exatos: `store_id` (obrig.), `apply_to` = `agendamento|comparecimento|fechamento`,
  `preset` = `today|month|from_today|custom`, `from`/`to` = `YYYY-MM-DD` (com `custom`),
  `search`, `page` (1-based), `page_size` (default 25; `100` aceito). Para TODOS os
  agendamentos do dia: `page_size=100` e pagine enquanto `page*page_size < total`.
- Cada item é o **lead completo** (mesmo shape do B1/atalho 4).

### C5. ⭐ Fuso

Sim: **datas e horas naïve em horário local (Brasília) em toda a API** — campos `date`
(`data_agendamento`, `data_compareceu`, ...) e `hora_agendamento`. Exceção: `created_at`/
`updated_at` são timestamptz UTC ISO. Não há loja com fuso diferente nem previsão —
trate como `America/Sao_Paulo` no adapter.

---

## Bloco D — Handoff

### D1. Atribuir

```
PATCH /crm/leads/{id}
REQ:  {"assigned_to": "062961dc-...", "observacoes": "[IA→humano] resumo do papo"}
→ 200: lead completo com assigned_to preenchido
```

(`vendedor_id` idem, pelo mesmo endpoint.)

### D2. Time da loja

```
GET /stores/{store_id}/team
→ 200: [{"id": "924eed49-...", "email": "gerente...", "name": "Gerente — 11fc",
         "role": "shop_user", "active": true}, ...]
```

⚠️ O response **não traz `shop_role`** (sdr/vendedor/gerente). Se o agente precisar
escolher "um SDR", hoje não dá para distinguir por essa rota — dá para expormos
`shop_role` aqui num PR pequeno; peçam se precisarem.

### D3. ⭐ Contexto do handoff

- **`crm_activity_log` NÃO é exposto** por API (é gravado internamente na troca de etapa). Não há endpoint de nota/atividade.
- Gravar em `observacoes` é aceitável, **mas o PATCH SOBRESCREVE** (update simples).
- ⚠️ Também **não existe `GET /crm/leads/{id}`** (só a lista). Para fazer append seguro:
  `GET /crm/leads?store_id=...` → achar o lead → concatenar → `PATCH observacoes`.
  Se preferirem, expomos `GET /crm/leads/{id}` e/ou um endpoint de nota — PR pequeno.

---

## Bloco E — Operacional

### E1. Ambiente

Staging ainda não deployado (Coolify pendente). Local completo: `ONBOARDING.md` do
repo (Docker, 2 comandos, seed com 5 lojas/funis/SDRs/leads). Credenciais demo:
`carlos@trivus.local / demo123` (client — o perfil recomendado p/ o agente),
`admin@trivus.local / admin123`. `store_id`: via `GET /stores/mine` (client) ou
`GET /admin/stores` (admin) — os UUIDs mudam a cada re-seed.

### E2. Rate limit

**Não há** rate limit hoje (nenhum middleware; verificado no código).

### E3. ⭐ Webhook Z-API da loja piloto

```
PATCH /admin/stores/{store_id}
REQ:  {"zapi_webhook_enabled": false}
→ 200: {"id": "...", "nome_fantasia": "AutoStar — Matriz", "crm_enabled": true, "active": true}
```

Com a flag `false` o webhook do trivus-api ignora a loja — sem lead em dobro.
(No seed demo ela nasce `true`; desliguem na piloto.)

### E4. Catálogo de erros (todos reais)

| Status | Corpo |
|---|---|
| 400 (regra de etapa) | `{"error": "Preencha os campos obrigatórios: Cidade, Modelo do veículo, Ano."}` |
| 401 | `{"error": "Token ausente"}` |
| 403 (rbac) | `{"error": "Acesso negado para o seu perfil."}` |
| 403 (feature) | `{"error": "feature_locked", "feature_key": "agenda"}` |
| 404 | `{"error": "Lead não encontrado"}` |
| 422 (validação) | `{"detail": [{"type": "missing", "loc": ["body", "store_id"], "msg": "Field required", "input": {...}}]}` |

> O 400 acima vem do `PATCH /crm/leads/{id}/stage` (mover etapa valida os campos
> obrigatórios da etapa destino — `domain/stage_rules.py`). O agente normalmente
> não move etapa, mas se mover, trate esse formato.

---

## Extras não perguntados que importam

- `DELETE /crm/leads/{id}` → 204 (existe, sem gate).
- `GET /stores/mine` → lojas vinculadas ao usuário do token (novo nesta develop).
- Não há `GET /crm/leads/{id}` nem busca server-side — pedir se fizer falta.
- Branch de trabalho da API: **`develop`** (main/master/legacy não recebem push direto).
