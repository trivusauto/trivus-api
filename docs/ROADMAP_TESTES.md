# Roadmap de Testes — Trivus (cobertura 100% para produção)

> Objetivo: validar ponto a ponto antes do go-live. Marque cada item. As colunas
> **Auto** (teste automatizado existe) e **Manual** (precisa validação humana/QA).
> Legenda de estado: ✅ pronto/coberto · 🟡 parcial · ⬜ pendente.

---

## 0. Estado atual do sistema (baseline honesto)

| Área | Estado | Observação |
|---|---|---|
| Backend (trivus-api, FastAPI) | ✅ | 161 testes (unit+integração+e2e) verdes, ruff+mypy limpos. Branch `develop`. |
| Segurança (multi-tenant, input) | ✅ | Stress test 21/07 → 0 críticos, 0 high após correções (isolamento por loja + 4xx). |
| Front novo (trivus-web, Next 16) | 🟡 | Todas as 24 telas funcionam (validado no browser em dev), mas **0 testes automatizados**. Branch `release/new-web`. |
| Marketing (CPL/CAC/ROAS) | ✅ | Cruza CRM↔financeiro de verdade. **Investimento é MANUAL** (Lançamento diário). |
| Integração Meta Ads | ⬜ | **Não iniciada.** Ver §Marketing/Meta. |
| Migração de dados (Plano 11) | ⬜ | Cutover do Supabase antigo → banco novo, ainda não ensaiado com dados reais. |
| Deploy Coolify | 🟡 | Documentado (docs/DEPLOY_COOLIFY.md) + CI pronto; **secrets/ambiente não configurados**. |
| Agente WhatsApp ↔ API | 🟡 | Contrato mapeado (docs/INTEGRACAO_AGENTE.md). Adapter do agente a construir. |

**Maior lacuna para "100%": testes automatizados de front (E2E) e a migração de dados real (Plano 11).**

---

## Marketing + conexão com a Meta — em que pé está

**O que JÁ funciona (hoje, sem Meta):**
- Campanhas como entidade (CRUD), vínculo campanha↔lead (manual no drawer ou auto via `link_code` do WhatsApp).
- Funil de custos receptivo: CPL → custo/classificado → custo/qualificado → custo/agendado → CAC, com sinaleiros (verde/amarelo/vermelho).
- ROAS/ROI: faturamento (receita das vendas do CRM) ÷ investimento. **Cruzamento real com o CRM/financeiro.**
- Funil por campanha (usa `budget` da campanha), comparativo entre campanhas.
- Metas de investimento + relatórios meta×realizado (gateado por plano).

**O que é MANUAL hoje e a Meta automatizaria:** o **valor investido por dia** (digitado no Lançamento diário) e o `budget` por campanha.

**Conectar a Meta Ads — não iniciado. Caminho (2 frentes):**

1. **Do lado da Meta (burocracia, é o caminho crítico de prazo):**
   - Business Manager verificado (CNPJ).
   - App tipo *Business* + produto *Marketing API*.
   - Contas de anúncio dos clientes compartilhadas com o BM da Trivus (agência provavelmente já tem).
   - System User com permissão `ads_read` + token (não expira).
   - Para ler contas de **vários clientes** em escala → **App Review / Advanced Access** da Meta.

2. **Do lado do Trivus (~1-2 dias de código, posso fazer com a Meta mockada):**
   - Migration: `meta_campaign_id` em campanhas + `meta_ad_account_id` na loja + tabela `campaign_daily_spend`.
   - Adapter `integrations/meta` (Graph API `/act_X/insights?level=campaign&time_increment=1&fields=spend,...`).
   - Sync diário (n8n/cron) → grava gasto por campanha/dia → funil de custos passa a ser automático.
   - Telas: campo "ID campanha Meta" + "conta de anúncios" na loja.

> Recomendação: começar a burocracia da Meta AGORA (leva dias/semanas) e, em paralelo, eu construo o lado do Trivus com mock — no dia que o token sair, é só ligar.

---

## FASE 0 — Pré-requisitos do ambiente de teste (⬜)

- [ ] Ambiente de **staging** no Coolify (API + web + Postgres), separado de produção.
- [ ] Dados de teste: rodar `seed_demo` OU importar um **snapshot anonimizado** de produção.
- [ ] 1 usuário de teste por papel: `admin`, `client` (dono), `shop_user` (sdr, vendedor, gerente, administrativo).
- [ ] Lojas cobrindo os planos: Full, Performance, Essencial, e uma **suspensa**.
- [ ] Ferramenta de E2E de front instalada (**Playwright** — hoje não existe nenhum teste de front).

---

## FASE 1 — Autenticação & Autorização (🟡 backend coberto, front não)

- [x] Login válido/ inválido, senha errada, campos faltando → 200/401/422. *(auto: test_auth)*
- [x] JWT ausente/malformado/assinatura trocada → 401 sem vazar stack. *(auto: stress test)*
- [ ] Expiração do token (7 dias) → 401 e re-login no front (cookie httpOnly). *(manual)*
- [x] **Isolamento multi-tenant**: client/shop_user não acessam loja alheia → 403. *(auto: test_multitenant)*
- [x] shop_user só vê os próprios leads. *(auto)*
- [x] Rotas `/admin/*` bloqueadas para client/shop_user → 403. *(auto)*
- [ ] BFF/cookie: logout limpa cookie; proxy `/api/backend` injeta Bearer; rota protegida redireciona p/ login. *(manual/front E2E)*
- [ ] **Feature gates** por plano: cada tela bloqueada mostra upsell correto (Essencial sem Marketing/Métricas; suspensa tudo bloqueado). *(manual/front E2E)*

---

## FASE 2 — Testes funcionais por módulo/tela (E2E, por papel)

Para **cada** tela: abrir como admin, como dono, como equipe; criar/editar/excluir; validar erros; conferir que os dados batem com o banco.

### 2.1 CRM / Kanban ⬜(front E2E)
- [ ] Criar lead (modal) → cai na 1ª etapa; auto-posiciona se campos completos.
- [ ] Arrastar entre etapas; bloqueio por campos obrigatórios (mensagem correta por etapa).
- [ ] Auto-avanço ao salvar no drawer (agendar/comparecer/comprar/fechar).
- [ ] Coluna **RESGATE**: entra só via arrasto; valor pretendido no card.
- [ ] Carimbo automático de data (comprado/vendido) + edição retroativa.
- [ ] Filtro por coluna; filtro por período por data de cada coluna.
- [ ] Excluir lead; drawer de agendamento/comparecimento/fechamento.
- [x] Regras de etapa idênticas ao legado. *(auto: test_stage_rules, test_crm_patches)*

### 2.2 Agenda ⬜
- [ ] Lista e calendário; filtro por agendamento/comparecimento/fechamento; presets (hoje/mês/custom); paginação; busca.

### 2.3 Marketing ⬜
- [ ] Funil de custos (CPL→CAC) com sinaleiros; investimento vindo do Lançamento diário.
- [ ] ROAS/ROI batendo com receita das vendas do CRM.
- [ ] Funil por campanha; comparativo; troca de período.

### 2.4 Campanhas ⬜ — CRUD, vínculo com leads.
### 2.5 Relatórios ⬜ — meta×realizado por origem; custos gateados por plano (Essencial não vê).
### 2.6 Projeções ⬜ — Meta/Realizado/Projetando; validação de mês/ano.
### 2.7 Metas ⬜ — upsert por loja+ano+mês+origem (só admin edita).
### 2.8 Planos de Ação ⬜ — kanban a_fazer/em_andamento/concluído.
### 2.9 Lançamento diário ⬜ — upsert por loja+data+origem; investimento alimenta o marketing.
### 2.10 Dashboard ⬜ — KPIs, funil, série 12 meses coerentes com os leads.
### 2.11 Ecossistema (vitrine) ⬜ — cards, "tenho interesse" registra.

### Admin da holding ⬜
- [ ] Lojas (flags, token webhook, criar loja clona funil).
- [ ] Usuários (portal + equipe; vincular lojas).
- [ ] Empresas, Planos (service_keys), Serviços (feature_keys), Assinaturas (suspender/reativar), Interesses (kanban).

---

## FASE 3 — Regras de negócio (🟡)

- [x] Entitlements: assinatura utilizável ∧ plano tem serviço ∧ ligado na loja → união das feature_keys. *(auto: test_ecosystem)*
- [ ] Assinatura **suspensa/trial expirado** → bloqueia na hora. *(auto parcial; validar trial expirado)*
- [x] Cálculos marketing (CPL/CAC/ROAS/traffic light) + divisão por zero. *(auto: test_metrics_core; stress: loja vazia ok)*
- [x] Auto-avanço só avança, nunca rebaixa (preserva RESGATE). *(lógica; falta e2e dedicado)*
- [ ] `require_campaign_on_lead`: bloqueia avanço sem campanha. *(validar)*

---

## FASE 4 — Integrações (⬜)

- [ ] **Webhook Z-API**: payload real do WhatsApp cria lead + round-robin de SDR + auto-match de campanha por `link_code`. **Validar payload CTWA real com o Alexis.**
- [ ] **n8n**: disparos em massa (bulk_send) e notificação de interesses (token `x-n8n-token`).
- [ ] **Billing gateway**: `POST /integrations/billing/events` com o framework de pagamento (token `x-billing-token`), ligado por env.
- [ ] **Meta Ads**: quando construído (ver §Marketing).
- [ ] **Agente WhatsApp**: adapter consumindo a API (docs/INTEGRACAO_AGENTE.md) — ligar `zapi_webhook_enabled=false` na loja piloto p/ não duplicar.

---

## FASE 5 — Não-funcional (🟡)

- [x] Segurança: multi-tenant, injection, JWT, 500→4xx. *(stress test 21/07)*
- [ ] **Paginação** de `GET /crm/leads` (hoje carrega tudo) — validar com loja de milhares de leads.
- [ ] Carga: 50-100 usuários simultâneos nas telas pesadas (dashboard/relatórios). *(k6/locust)*
- [ ] Backup/restore do Postgres testado (restaurar num ambiente limpo).
- [ ] Logs e observabilidade (erros 5xx monitorados).
- [ ] Rate limiting (hoje não há) — decidir se entra antes do go-live.

---

## FASE 6 — Migração de dados (Plano 11 / cutover) (⬜ — CRÍTICO)

- [ ] Ensaio do ETL Supabase antigo → banco novo (com string **read-only** do banco atual, com o humano presente).
- [ ] Validação de **paridade**: contagens (leads, lojas, usuários, metas) batem old×new; amostragem de registros.
- [ ] Step 1b: criar company + assinatura `consultoria_full` para clientes atuais (legado sem gate).
- [ ] Janela de virada única ensaiada; plano de rollback.
- [ ] Datas locais (não UTC) preservadas.

---

## FASE 7 — Deploy / Infra (🟡)

- [ ] Coolify: DB + API (Dockerfile, porta 3001, health `/health`) + secrets (JWT_SECRET, DATABASE_URL asyncpg, N8N_*, BILLING_*).
- [ ] Deploy automático: push na main verde → webhook Coolify (COOLIFY_WEBHOOK_URL/TOKEN).
- [ ] Migrations rodam sozinhas no boot (`alembic upgrade head`).
- [ ] Front no Coolify (Dockerfile standalone, BACKEND_URL apontando p/ API interna; cookie secure via x-forwarded-proto atrás do Traefik).
- [ ] HTTPS/domínio; teste de rollback (voltar versão anterior).
- [ ] ⚠️ Conflito de portas com a stack `checkout` local — em produção não se aplica, mas em dev usar portas alternativas.

---

## FASE 8 — Aceite final / Go-live checklist (⬜)

- [ ] Todos os itens acima ✅ em staging.
- [ ] Smoke test em produção logo após deploy (login, criar lead, dashboard).
- [ ] Rotacionar segredos que já foram expostos em chat (GitHub token, Z-API, Vercel etc.).
- [ ] Apagar a pasta antiga `trivus-backend/`.
- [ ] Plano de suporte pós-lançamento (quem monitora, como reverter).

---

## Prioridade sugerida (ordem de execução)

1. **Fase 6 (migração)** e **Fase 7 (deploy)** — sem isso não há produção.
2. **Fase 2 (E2E de front com Playwright)** — a maior lacuna de cobertura.
3. **Fase 4 (integrações)** — Z-API + agente são o coração da entrada de leads.
4. **Meta Ads** — começar a burocracia já, código em paralelo.
5. **Fase 5 (carga/paginação/backup)** — antes de escalar clientes.

> Backend + segurança já estão em bom estado (161 testes + stress test). O trabalho de "100%" concentra-se em: **E2E de front, migração real, integrações e deploy**.
