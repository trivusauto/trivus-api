# Modelo-Alvo do Banco (schema-alvo) — APROVADO

> Versão limpa e corrigida do banco do Trivus, derivada do domínio em [`../MIGRACAO_BACKEND.md`](../MIGRACAO_BACKEND.md) §4.
> **Status: ✅ aprovado** com as recomendações D1–D7 (ver [§ Decisões](#decisões-a-confirmar)). É a fonte da verdade para a migration inicial (Plano 02) e o de-para da migração de dados (Plano 11).
> **Extensões:** tabela 16 (marketing — spec `MUDANCAS_MARKETING_RELATORIOS.md`) e tabelas 17–23 (ecossistema — spec [`../ECOSSISTEMA_TRIVUS.md`](../ECOSSISTEMA_TRIVUS.md)). **Total: 23 tabelas.**
> **Ordem de criação na migration:** `companies` → `stores` → ... → `services` antes de `store_services`/`service_interests` (FKs). Se preferir, crie as FKs de `stores.company_id` via `ALTER TABLE` no final.

## Convenções

- **PK** `uuid` com `DEFAULT gen_random_uuid()` (requer extensão `pgcrypto`).
- **Datas/hora** sempre `date` ou `timestamptz` (nunca texto). Dinheiro `numeric(14,2)`.
- **Relacionamentos** sempre com **FK declarada** (hoje são só convenção).
- **`store_id`** substitui `client_id` em toda tabela de negócio (sempre referencia `stores.id`).
- **Soft-delete** via coluna `active` (não deletamos lojas/usuários de verdade) → FKs para `stores`/`users` usam `RESTRICT`/`SET NULL`, não `CASCADE`.
- **Enums** via `CHECK` (valores na spec §5).

---

## 1. `stores` — dados da loja (fonte única)

```sql
CREATE TABLE stores (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id           uuid REFERENCES companies(id) ON DELETE RESTRICT,  -- empresa dona (ecossistema; NULL até o ETL — E5)
  nome_fantasia        text NOT NULL,
  razao_social         text,
  cnpj                 text,
  nome_responsavel     text,
  cep                  text, logradouro text, numero text,
  complemento          text, bairro text, cidade text, estado text,
  crm_enabled          boolean NOT NULL DEFAULT false,
  zapi_webhook_enabled boolean NOT NULL DEFAULT false,
  require_campaign_on_lead boolean NOT NULL DEFAULT false,  -- exige campanha p/ avançar lead receptivo (módulo marketing)
  webhook_token        text UNIQUE,
  shop_role_labels     jsonb,
  utiliza_ia           boolean NOT NULL DEFAULT false,           -- veio de users (legado)
  last_assigned_sdr_id uuid REFERENCES users(id) ON DELETE SET NULL,  -- ponteiro round-robin (mora SÓ aqui)
  active               boolean NOT NULL DEFAULT true,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now()
);
```

## 2. `users` — credenciais e perfil de acesso (só isso)

```sql
CREATE TABLE users (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email                    text NOT NULL UNIQUE,
  password_hash            text NOT NULL,
  name                     text,
  role                     text NOT NULL CHECK (role IN ('admin','client','shop_user')),
  parent_store_id          uuid REFERENCES stores(id) ON DELETE CASCADE,   -- só p/ shop_user (era parent_client_id)
  shop_role                text CHECK (shop_role IN ('sdr','vendedor','administrativo','gerente')),
  menu_permissions         jsonb NOT NULL DEFAULT '[]',
  can_see_unassigned_leads boolean NOT NULL DEFAULT false,
  active                   boolean NOT NULL DEFAULT true,
  created_at               timestamptz NOT NULL DEFAULT now()
  -- REMOVIDOS (eram duplicação de loja): nome_fantasia, razao_social, cnpj, endereço,
  -- crm_enabled, zapi_webhook_enabled, webhook_token, shop_role_labels, last_assigned_sdr_id
);
CREATE INDEX idx_users_parent_store ON users (parent_store_id);
```
**De-para:** `parent_client_id → parent_store_id`. As colunas de loja saem (migram para `stores`).

## 3. `user_store_access` — vínculo N:N (usuário ↔ lojas)

```sql
CREATE TABLE user_store_access (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
  store_id   uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  is_owner   boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, store_id)
);
CREATE INDEX idx_usa_user ON user_store_access (user_id);
```

## 4. `crm_funnels` — funis (template + clones por loja)

```sql
CREATE TABLE crm_funnels (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id           uuid REFERENCES stores(id) ON DELETE CASCADE,   -- NULL = funil-template
  name               text NOT NULL,
  sort_order         int NOT NULL DEFAULT 0,
  is_template        boolean NOT NULL DEFAULT false,
  template_source_id uuid REFERENCES crm_funnels(id) ON DELETE SET NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  CHECK ( (is_template AND store_id IS NULL) OR (NOT is_template AND store_id IS NOT NULL) )
);
CREATE INDEX idx_funnels_store ON crm_funnels (store_id);
```

## 5. `crm_funnel_stages` — colunas do funil

```sql
CREATE TABLE crm_funnel_stages (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  funnel_id         uuid NOT NULL REFERENCES crm_funnels(id) ON DELETE CASCADE,
  name              text NOT NULL,
  sort_order        int NOT NULL DEFAULT 0,
  template_stage_id uuid REFERENCES crm_funnel_stages(id) ON DELETE SET NULL
);
CREATE INDEX idx_stages_funnel ON crm_funnel_stages (funnel_id);
```

## 6. `crm_funnel_leads` — lead no Kanban (a tabela mais rica)

```sql
CREATE TABLE crm_funnel_leads (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id                  uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,        -- era client_id
  stage_id                  uuid NOT NULL REFERENCES crm_funnel_stages(id),
  sort_order                int NOT NULL DEFAULT 0,
  assigned_to               uuid REFERENCES users(id) ON DELETE SET NULL,
  vendedor_id               uuid REFERENCES users(id) ON DELETE SET NULL,
  agendado_por              uuid REFERENCES users(id) ON DELETE SET NULL,
  campaign_id               uuid REFERENCES marketing_campaigns(id) ON DELETE SET NULL,  -- campanha de origem (leads receptivos)
  -- captação
  funil                     text CHECK (funil IN ('receptivo','prospeccao_ativa','outros')),
  qualificado               boolean,
  origem_mkt                text,
  urgencia_venda            text,
  -- contato / veículo
  nome                      text,
  telefone                  text,
  lid                       text,
  bairro                    text,
  cidade                    text,
  modelo                    text, veiculo text, ano text, cor text,
  combustivel               text, quilometragem text, transmissao text,
  valor_tabela_fipe         numeric(14,2),
  tem_financiamento         boolean,
  saldo_quitacao            numeric(14,2),
  valor_pretendido          numeric(14,2),
  valor_compra              numeric(14,2),
  -- agenda
  data_agendamento          date,
  hora_agendamento          text,            -- "HH:MM:SS"
  data_marcacao_agendamento date,
  compareceu_agendamento    boolean,
  data_compareceu           date,
  -- fechamento
  fechou_negocio            boolean,
  data_fechou_negocio       date,
  receita                   numeric(14,2),
  despesa                   numeric(14,2),
  rentabilidade             numeric(14,2),
  observacoes               text,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_leads_store         ON crm_funnel_leads (store_id);
CREATE INDEX idx_leads_stage         ON crm_funnel_leads (stage_id);
CREATE INDEX idx_leads_store_created ON crm_funnel_leads (store_id, created_at);
CREATE INDEX idx_leads_assigned      ON crm_funnel_leads (assigned_to);
CREATE INDEX idx_leads_vendedor      ON crm_funnel_leads (vendedor_id);
CREATE INDEX idx_leads_telefone      ON crm_funnel_leads (store_id, telefone);
CREATE INDEX idx_leads_campaign      ON crm_funnel_leads (campaign_id);
```
**De-para:** `client_id → store_id`; datas texto → `date`; valores → `numeric(14,2)`.

## 7. `crm_lead_stage_history` — histórico de entrada em colunas

```sql
CREATE TABLE crm_lead_stage_history (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id    uuid NOT NULL REFERENCES crm_funnel_leads(id) ON DELETE CASCADE,
  stage_id   uuid NOT NULL REFERENCES crm_funnel_stages(id) ON DELETE CASCADE,
  entered_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_history_lead  ON crm_lead_stage_history (lead_id);
CREATE INDEX idx_history_stage ON crm_lead_stage_history (stage_id);
```

## 8. `crm_stage_cooling_rules` — alertas de lead parado

```sql
CREATE TABLE crm_stage_cooling_rules (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stage_id        uuid NOT NULL REFERENCES crm_funnel_stages(id) ON DELETE CASCADE,
  hours_threshold int NOT NULL,
  card_color      text NOT NULL DEFAULT '#facc15',
  message         text NOT NULL DEFAULT 'Lead esfriando',
  sort_order      int NOT NULL DEFAULT 0
);
CREATE INDEX idx_cooling_stage ON crm_stage_cooling_rules (stage_id);
```

## 9. `crm_activity_log` — auditoria do CRM

```sql
CREATE TABLE crm_activity_log (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id      uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  action        text NOT NULL,
  entity_type   text,
  entity_id     uuid,
  payload       jsonb NOT NULL DEFAULT '{}',
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_activity_store ON crm_activity_log (store_id, created_at);
```

## 10. `leads` — leads legado (modo sem CRM)

```sql
CREATE TABLE leads (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id                uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  name                    text, phone text, car text, city text,
  origin                  text CHECK (origin IN ('receptivo','prospeccao','outros')),
  origin_custom           text,
  entry_date              date,
  qualified               boolean NOT NULL DEFAULT false,
  disqualified            boolean NOT NULL DEFAULT false,
  disqualification_reason text,
  scheduled               boolean NOT NULL DEFAULT false,
  attended                boolean NOT NULL DEFAULT false,
  converted               boolean NOT NULL DEFAULT false,
  profitability           numeric(14,2),
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_legacy_leads_store ON leads (store_id);
```

## 11. `daily_indicators` — indicadores diários (modo sem CRM)

```sql
CREATE TABLE daily_indicators (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id        uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  reference_date  date NOT NULL,
  origin          text NOT NULL CHECK (origin IN ('receptivo','prospeccao','outros')),
  origin_custom   text,
  total_leads     int NOT NULL DEFAULT 0,
  qualified_leads int NOT NULL DEFAULT 0,
  classified_leads int NOT NULL DEFAULT 0,   -- etapa CLASSIFICADOS (módulo marketing)
  scheduled_leads int NOT NULL DEFAULT 0,
  attended_leads  int NOT NULL DEFAULT 0,
  converted_leads int NOT NULL DEFAULT 0,
  profitability   numeric(14,2),
  daily_expenses  numeric(14,2),
  marketing_investment numeric(14,2),        -- investimento em marketing do dia (módulo marketing; distinto de despesas)
  notes           text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_id, reference_date, origin)
);
```

## 12. `goals` — metas mensais

```sql
CREATE TABLE goals (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id            uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  month               int NOT NULL CHECK (month BETWEEN 1 AND 12),
  year                int NOT NULL,
  origin              text NOT NULL CHECK (origin IN ('receptivo','prospeccao','outros')),
  leads_quantity       int NOT NULL DEFAULT 0,
  qualified_quantity   int NOT NULL DEFAULT 0,
  scheduled_quantity   int NOT NULL DEFAULT 0,
  attended_quantity    int NOT NULL DEFAULT 0,
  conversions_quantity int NOT NULL DEFAULT 0,
  profitability_goal   numeric(14,2),
  average_ticket_goal  numeric(14,2),
  marketing_investment_goal numeric(14,2),   -- meta de investimento em marketing do mês (módulo marketing)
  created_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_id, year, month, origin)        -- ⚠️ confirmar (ver decisões)
);
```

## 13. `action_plans` — planos de ação

```sql
CREATE TABLE action_plans (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id    uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  title       text NOT NULL,
  description text,
  status      text NOT NULL DEFAULT 'a_fazer' CHECK (status IN ('a_fazer','em_andamento','concluido')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_action_plans_store ON action_plans (store_id);
```

## 14. `bulk_sends` — disparos em massa (admin)

```sql
CREATE TABLE bulk_sends (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title            text,
  total_contacts   int NOT NULL DEFAULT 0,
  success_count    int NOT NULL DEFAULT 0,
  error_count      int NOT NULL DEFAULT 0,
  status           text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','running','paused','completed')),
  message_template text,
  variation_1 text, variation_2 text, variation_3 text, variation_4 text, variation_5 text,
  delay_min_sec    int NOT NULL DEFAULT 30,
  delay_max_sec    int NOT NULL DEFAULT 30,
  started_at       timestamptz,
  completed_at     timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);
```

## 15. `bulk_send_contacts` — contatos do disparo

```sql
CREATE TABLE bulk_send_contacts (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bulk_send_id    uuid NOT NULL REFERENCES bulk_sends(id) ON DELETE CASCADE,
  phone           text NOT NULL,
  variation_index int NOT NULL DEFAULT 0,
  status          text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','error')),
  scheduled_at    timestamptz,
  sent_at         timestamptz,
  error_message   text,
  UNIQUE (bulk_send_id, phone)
);
```
> A view `bulk_send_contacts_ordered` deixa de existir — a ordenação `pending→sent→error` vira `ORDER BY` na query.

## 16. `marketing_campaigns` — campanhas de marketing (módulo marketing)

```sql
CREATE TABLE marketing_campaigns (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id   uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  name       text NOT NULL,
  link_code  text,                            -- identificador p/ auto-match do lead via link de WhatsApp (opcional)
  started_at date NOT NULL,
  ended_at   date,                            -- NULL = campanha ativa
  budget     numeric(14,2),                   -- orçamento previsto (usado como investimento no funil por campanha)
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_campaigns_store ON marketing_campaigns (store_id);
```
> Cadastrada pela pré-vendas ou admin da loja. Leads **receptivos** apontam para ela via `crm_funnel_leads.campaign_id` (spec da reunião de 02/07/2026, `MUDANCAS_MARKETING_RELATORIOS.md`).

---

# Ecossistema (spec [`../ECOSSISTEMA_TRIVUS.md`](../ECOSSISTEMA_TRIVUS.md))

## 17. `companies` — empresa/conta comercial da holding

```sql
CREATE TABLE companies (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name             text NOT NULL,
  cnpj             text,
  responsible_name text,
  active           boolean NOT NULL DEFAULT true,
  created_at       timestamptz NOT NULL DEFAULT now()
);
```
> Quem assina o contrato. Uma empresa tem N lojas (`stores.company_id`).

## 18. `plans` — planos comerciais

```sql
CREATE TABLE plans (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key          text NOT NULL UNIQUE,          -- saas_starter | saas_pro | consultoria_full | custom...
  name         text NOT NULL,
  service_keys jsonb NOT NULL DEFAULT '[]',   -- keys de services que o plano PERMITE (validado na aplicação)
  max_stores   int,                           -- NULL = ilimitado
  price_month  numeric(14,2),                 -- informativo (cobrança manual na v1)
  active       boolean NOT NULL DEFAULT true,
  created_at   timestamptz NOT NULL DEFAULT now()
);
```

## 19. `subscriptions` — assinatura da empresa

```sql
CREATE TABLE subscriptions (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id              uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  plan_id                 uuid NOT NULL REFERENCES plans(id),
  status                  text NOT NULL CHECK (status IN ('trialing','active','suspended','canceled')),
  trial_ends_at           date,               -- trial expira sozinho na leitura (sem cron)
  billing_mode            text NOT NULL DEFAULT 'manual' CHECK (billing_mode IN ('manual','gateway')),
  gateway_customer_id     text,               -- preenchidos quando o gateway (Asaas) ligar
  gateway_subscription_id text,
  started_at              date,
  canceled_at             date,
  notes                   text,
  created_at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_subscriptions_company ON subscriptions (company_id);
```

## 20. `services` — catálogo de serviços do ecossistema (CRUD do admin)

```sql
CREATE TABLE services (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key          text NOT NULL UNIQUE,          -- slug estável, imutável após criação
  name         text NOT NULL,
  type         text NOT NULL CHECK (type IN ('software','humano')),
  what_it_is   text,                          -- "o que é" (catálogo)
  what_it_does text,                          -- "o que faz" (detalhe)
  upsell_pitch text,                          -- copy do card de bloqueio/upsell
  feature_keys jsonb NOT NULL DEFAULT '[]',   -- o que desbloqueia (picklist do registro de keys do código)
  sort_order   int NOT NULL DEFAULT 0,
  active       boolean NOT NULL DEFAULT true, -- soft-delete
  created_at   timestamptz NOT NULL DEFAULT now()
);
```
> Feature keys têm grão livre (módulo, tela, card, área — ex.: `metrics.reports.costs`). Serviços humanos (consultoria, capacitação, agência) têm `feature_keys = []`.

## 21. `store_services` — o híbrido: serviço ligado por loja

```sql
CREATE TABLE store_services (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id    uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  service_key text NOT NULL REFERENCES services(key),
  enabled     boolean NOT NULL DEFAULT true,
  UNIQUE (store_id, service_key)
);
```

## 22. `service_interests` — upsell (interesse em serviço)

```sql
CREATE TABLE service_interests (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id   uuid REFERENCES companies(id) ON DELETE SET NULL,
  store_id     uuid REFERENCES stores(id) ON DELETE SET NULL,
  service_key  text NOT NULL REFERENCES services(key),
  requested_by uuid REFERENCES users(id) ON DELETE SET NULL,
  status       text NOT NULL DEFAULT 'novo' CHECK (status IN ('novo','contatado','convertido','descartado')),
  notes        text,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_interests_status ON service_interests (status, created_at);
```
> O `POST` que cria o interesse também dispara a notificação n8n ao comercial da holding.

## 23. `subscription_payments` — eventos de pagamento (do framework de cobrança do dono)

```sql
CREATE TABLE subscription_payments (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id uuid NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
  external_id     text,                       -- id do pagamento no framework/gateway
  gateway         text,                       -- qual gateway processou (informativo)
  event_type      text NOT NULL,              -- payment_confirmed | payment_failed | payment_overdue | payment_refunded
  status          text NOT NULL,              -- confirmed | failed | overdue | refunded
  amount          numeric(14,2),
  paid_at         timestamptz,
  payload         jsonb NOT NULL DEFAULT '{}',-- evento bruto recebido (auditoria)
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_subpay_sub ON subscription_payments (subscription_id, created_at);
```
> Alimentada pelo `POST /integrations/billing/events` (chamado pelo framework de pagamentos do dono — E1). O sistema **não** integra gateway diretamente.

---

## Decisões a confirmar

| # | Tema | Pergunta | Minha recomendação |
|---|------|----------|--------------------|
| D1 | Deletar loja | Permitir deletar uma loja com dados? | **Não** — usar `active=false` (soft-delete). FKs para `stores` ficam `RESTRICT`/`SET NULL` (já está assim). |
| D2 | Dedup de lead | `crm_funnel_leads (store_id, telefone)` deve ser `UNIQUE`? | **Não unique** (índice normal). O webhook dedup por variantes do 9º dígito na aplicação (spec §6.12); unique rígido quebraria isso. |
| D3 | Unicidade de meta | `goals` único por `(store_id, year, month, origin)`? | **Sim** (evita meta duplicada). Incluído acima — confirmar. |
| D4 | `hora_agendamento` | Tipo `text "HH:MM:SS"` ou `time`? | **`text`** por ora (igual ao atual; menos atrito no port). Migrar p/ `time` depois é fácil. |
| D5 | `ano` do veículo | `text` ou `int`? | **`text`** (hoje aceita coisas como "2020/2021"). |
| D6 | Disparos por loja | `bulk_sends` precisa de `store_id`? | **Não** (hoje é recurso global do admin). Adicionar depois se virar por-loja. |
| D7 | `updated_at` | Atualizar via trigger no banco ou na aplicação? | **Aplicação** (o repositório seta no update) — mais simples e testável. |

---

*Rascunho gerado a partir de `MIGRACAO_BACKEND.md` §4–5. Aprovar antes de virar a migration inicial (Plano 02).*
