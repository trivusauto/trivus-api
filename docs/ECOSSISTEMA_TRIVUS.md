# Spec — Ecossistema Trivus (empresas, assinaturas, serviços e upsell)

> **Contexto de negócio:** a Trivus é uma holding (consultoria + capacitação + agência de marketing) e o sistema é a plataforma desse ecossistema. Empresas podem entrar como **SaaS puro**, usar **partes** dos serviços, ou ser clientes de **consultoria completa** — e migrar entre esses modos sem trocar de sistema. O sistema também **promove e vende** os serviços do ecossistema para quem ainda não os tem.
>
> **Status:** design aprovado em conversa (jul/2026). Fonte para o Plano 12.

---

## 1. Os 4 conceitos (separação central)

```
1. COMPANY (empresa/conta comercial)  ← quem assina o contrato com a holding
      └── 2. STORES (lojas/tenants)   ← quem opera o sistema (já existia)
3. SUBSCRIPTION (plano + status)      ← o que a empresa contratou e como paga
4. ENTITLEMENTS (feature keys)        ← o que está desbloqueado, por loja
```

Decisões estruturais (do dono):
- **Modelo híbrido:** a assinatura pertence à **empresa** (1 contrato, N lojas, limites do plano); os serviços **ligam/desligam por loja** dentro do que o plano permite.
- **Cobrança manual + trial automático** na v1; **gateway de pagamento desenvolvido mas desligado** (ver §6).
- **Upsell:** registro próprio (`service_interests`) + tela admin + **notificação automática via n8n** ao comercial da holding.

## 2. Catálogo de serviços — CRUD (não constantes)

`services` é uma **entidade gerenciada pelo admin** (CRUD completo): nome, o que é, o que faz, pitch de venda, tipo (`software` | `humano`) e **quais feature keys desbloqueia**.

**Separação chave-técnica × serviço-comercial:**
- **Feature keys** são definidas **no código** (registro versionado) — porque é o código que faz o gate. Granularidade livre: módulo, tela, **card ou área de tela**. Convenção: `modulo.tela.area` (ex.: `metrics.reports.costs` = só a coluna de custos do relatório).
- O **serviço** (CRUD) aponta para 1+ feature keys via **picklist** alimentada por `GET /ecosystem/feature-keys` (nunca digitação livre — typo não pode derrubar acesso).
- Serviços **humanos** (consultoria, capacitação, agência) têm `feature_keys = []`: não desbloqueiam software, existem para o catálogo/upsell.

**Registro inicial de feature keys (v1, cresce com o produto):**

| Key | Grão | O que gateia |
|---|---|---|
| `crm.kanban` | tela | Kanban de leads + funis + patches |
| `crm.activity_log` | área | histórico de atividades do lead |
| `agenda` | tela | agenda de agendamentos |
| `webhook.zapi` | módulo | captação automática WhatsApp |
| `metrics.dashboard` | tela | dashboard de KPIs |
| `metrics.reports` | tela | relatórios por origem |
| `metrics.reports.costs` | card/área | coluna de custos (CPL…CAC) no relatório |
| `metrics.marketing` | tela | funil de marketing + campanhas (telas) |
| `metrics.projections` | tela | projeções |
| `metrics.team` | tela | performance da equipe |
| `marketing.campaigns` | tela | cadastro de campanhas |
| `bulk_send` | módulo | disparos em massa |
| `indicators` | tela | modo indicadores |
| `goals` | tela | metas |
| `action_plans` | tela | planos de ação |

**Guarda-corpos do CRUD:** `key` do serviço é imutável após criação; excluir = `active=false` (bloqueado se o serviço estiver em algum plano); editar `feature_keys` muda o acesso dos assinantes **na hora** (comportamento desejado; a tela avisa).

## 3. Resolução de acesso (EntitlementService)

Uma regra única responde "a loja X pode usar a feature Y?":

```
feature Y desbloqueada para a loja X  ⇔
  assinatura da company de X está utilizável (active, ou trialing com trial_ends_at ≥ hoje)
  E ∃ serviço S: S ∈ plano da assinatura (plans.service_keys)
                 E S está ligado na loja X (store_services.enabled)
                 E Y ∈ S.feature_keys
```

**Aplicação (dois padrões):**
1. **Rota inteira:** dependency FastAPI `Depends(require_feature("agenda"))` → 403 com a key faltante (o front usa isso pra renderizar o card de upsell no lugar).
2. **Response-shaping** (para keys de card/área em endpoints mistos): o use case recebe o conjunto de keys desbloqueadas e **omite o bloco** (ex.: `costs` no relatório sai `null` sem `metrics.reports.costs`).

**Trial expira sozinho, sem cron:** `trialing` com `trial_ends_at < hoje` é tratado como suspenso **na leitura**. A tela admin destaca expirados.

**Legado sem ruptura:** `stores.crm_enabled` continua existindo (dispara o clone do funil-template); o EntitlementService o considera parte do "ligado na loja" para os serviços que contenham keys `crm.*`. Nota técnica no Plano 12.

**Front:** `GET /auth/me` (ou endpoint dedicado `GET /ecosystem/my-entitlements?store_id=`) passa a devolver o conjunto de feature keys desbloqueadas da loja selecionada — o front esconde/mostra telas, cards e áreas pela mesma key, e renderiza o upsell nos lugares bloqueados.

## 4. Upsell dentro do sistema

- `GET /ecosystem/services?store_id=` — catálogo: o que a empresa **tem** e **não tem**, com `name/what_it_is/upsell_pitch` e, para cada feature key bloqueada, **qual serviço a desbloqueia** (é assim que o front sabe qual card mostrar em cada área bloqueada).
- `POST /ecosystem/interests` — o clique "quero conhecer" grava o interesse **e dispara n8n** (e-mail/WhatsApp pro comercial da holding). Payload: company, loja, serviço, usuário.
- `GET /admin/interests` + `PATCH /admin/interests/{id}` — fila do comercial (`novo → contatado → convertido | descartado`).

## 5. Administração da holding (todas `require_roles("admin")`)

- CRUD de **serviços** (§2) e **planos** (`key, name, service_keys (picklist de serviços), max_stores, price_month informativo, active`).
- CRUD de **empresas** + vincular lojas (`stores.company_id`).
- **Assinaturas:** criar (empresa + plano + `trialing|active` + `trial_ends_at` — dias de trial definidos pelo admin ao criar), trocar plano, suspender, cancelar, anotar.
- Ligar/desligar serviços **por loja** (`store_services`) — validado contra o plano.
- Fila de interesses (upsell).

## 6. Cobrança — manual agora, integração com o framework de pagamentos do dono (desligada)

> **Decisão do dono:** já existe um **framework próprio rodando que integra vários gateways**. O sistema **não** integra gateway nenhum diretamente — ele expõe um **contrato de integração** e o framework é quem processa pagamentos e envia eventos. O sistema guarda as informações e reage.

- **v1 ativa:** cobrança manual (admin cria/ativa/suspende assinaturas) + **trial automático** (expira na leitura).
- **Integração desenvolvida e DESLIGADA** (`BILLING_GATEWAY_ENABLED=false`):
  - Endpoint `POST /integrations/billing/events`, protegido por token de integração (`x-billing-token`), que o framework chama a cada evento de pagamento.
  - **Contrato do evento** (o framework adapta os gateways para este formato): `{subscription_id, event_type: payment_confirmed|payment_failed|payment_overdue|payment_refunded, external_id, gateway, amount, paid_at, raw}`.
  - Cada evento é **persistido** em `subscription_payments` (histórico completo, payload bruto em jsonb) e, quando `subscriptions.billing_mode = 'gateway'`, transiciona o status: `payment_confirmed → active`; `payment_failed/overdue → suspended`. Cobrança manual e gateway **coexistem** via `billing_mode`.
  - Campos `gateway_customer_id`/`gateway_subscription_id` em `subscriptions` guardam os IDs do lado do framework.
- **`docs/BILLING_GATEWAY.md`** (entregável do Plano 12): o contrato do evento, autenticação, transições de status, e o passo a passo para concluir (configurar o framework para postar no endpoint, mapear os IDs, setar token/flag, testar em sandbox).

## 7. Modelo de dados (7 tabelas novas — MODELO_ALVO 16 → 23)

`companies`, `plans`, `subscriptions`, `services`, `store_services`, `service_interests`, `subscription_payments` + coluna `stores.company_id`. DDL completo no [`db/MODELO_ALVO.md`](./db/MODELO_ALVO.md) §17–23.

## 8. Migração dos clientes atuais (entra no Plano 11)

O ETL cria: 1 `company` por cliente atual da consultoria → assinatura `consultoria_full` **ativa** (billing manual) → todos os serviços ligados nas lojas → `stores.company_id` preenchido. **Ninguém percebe a mudança.** Seeds: plano `consultoria_full` + serviços iniciais (software com as keys da tabela do §2 + humanos com pitch).

## 9. Fora de escopo (v1)

- Self-checkout (upgrade self-service com pagamento) — quando o gateway ligar.
- Metas/limites de uso por serviço (ex.: nº de disparos/mês).
- Catálogo público/site de vendas.
- Integração Meta Ads (já fora do escopo do módulo marketing).

## 10. Decisões assumidas (validar na revisão)

| # | Decisão |
|---|---|
| E1 | **Sem adapter de gateway específico** — o framework de pagamentos do dono (que já integra vários gateways) chama o endpoint de eventos do sistema. O sistema só define o contrato, guarda e reage. |
| E2 | Dias de trial definidos **pelo admin ao criar a assinatura** (campo `trial_ends_at`), sem default global. |
| E3 | Empresa **sem nenhuma assinatura** = tudo bloqueado (só login e catálogo/upsell visíveis). |
| E4 | Feature keys de **card/área** usam response-shaping (o dado nem sai da API); keys de tela/módulo usam 403 na rota. |
| E5 | `stores.company_id` é `NULL` permitido durante a construção; o ETL do Plano 11 preenche e o admin exige empresa ao criar loja nova. |
| E6 | **Loja com `company_id NULL` = modo legado, sem gate** (acesso total). Mantém os módulos já construídos funcionando durante a execução dos planos; após o ETL do Plano 11, toda loja tem empresa e o gate vale para todas. |
| E7 | Admin Trivus **não é gateado** (`role=admin` enxerga tudo, sempre). |
