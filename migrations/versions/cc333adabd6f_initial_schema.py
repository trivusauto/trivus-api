"""initial schema

Revision ID: cc333adabd6f
Revises:
Create Date: 2026-07-01 15:04:14.479804

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'cc333adabd6f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
    op.execute("""
CREATE TABLE stores (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome_fantasia        text NOT NULL,
  razao_social         text,
  cnpj                 text,
  nome_responsavel     text,
  cep                  text, logradouro text, numero text,
  complemento          text, bairro text, cidade text, estado text,
  crm_enabled          boolean NOT NULL DEFAULT false,
  zapi_webhook_enabled boolean NOT NULL DEFAULT false,
  webhook_token        text UNIQUE,
  shop_role_labels     jsonb,
  utiliza_ia           boolean NOT NULL DEFAULT false,
  last_assigned_sdr_id uuid,
  active               boolean NOT NULL DEFAULT true,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now()
)
""")
    op.execute("""
CREATE TABLE users (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email                    text NOT NULL UNIQUE,
  password_hash            text NOT NULL,
  name                     text,
  role                     text NOT NULL CHECK (role IN ('admin','client','shop_user')),
  parent_store_id          uuid REFERENCES stores(id) ON DELETE CASCADE,
  shop_role                text CHECK (shop_role IN ('sdr','vendedor','administrativo','gerente')),
  menu_permissions         jsonb NOT NULL DEFAULT '[]',
  can_see_unassigned_leads boolean NOT NULL DEFAULT false,
  active                   boolean NOT NULL DEFAULT true,
  created_at               timestamptz NOT NULL DEFAULT now()
)
""")
    op.execute('CREATE INDEX idx_users_parent_store ON users (parent_store_id)')
    op.execute("""
ALTER TABLE stores
  ADD CONSTRAINT fk_stores_last_assigned_sdr
  FOREIGN KEY (last_assigned_sdr_id) REFERENCES users(id) ON DELETE SET NULL
""")
    op.execute("""
CREATE TABLE user_store_access (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
  store_id   uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  is_owner   boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, store_id)
)
""")
    op.execute('CREATE INDEX idx_usa_user ON user_store_access (user_id)')
    op.execute("""
CREATE TABLE crm_funnels (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id           uuid REFERENCES stores(id) ON DELETE CASCADE,
  name               text NOT NULL,
  sort_order         int NOT NULL DEFAULT 0,
  is_template        boolean NOT NULL DEFAULT false,
  template_source_id uuid REFERENCES crm_funnels(id) ON DELETE SET NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  CHECK ( (is_template AND store_id IS NULL) OR (NOT is_template AND store_id IS NOT NULL) )
)
""")
    op.execute('CREATE INDEX idx_funnels_store ON crm_funnels (store_id)')
    op.execute("""
CREATE TABLE crm_funnel_stages (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  funnel_id         uuid NOT NULL REFERENCES crm_funnels(id) ON DELETE CASCADE,
  name              text NOT NULL,
  sort_order        int NOT NULL DEFAULT 0,
  template_stage_id uuid REFERENCES crm_funnel_stages(id) ON DELETE SET NULL
)
""")
    op.execute('CREATE INDEX idx_stages_funnel ON crm_funnel_stages (funnel_id)')
    op.execute("""
CREATE TABLE crm_funnel_leads (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id                  uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  stage_id                  uuid NOT NULL REFERENCES crm_funnel_stages(id),
  sort_order                int NOT NULL DEFAULT 0,
  assigned_to               uuid REFERENCES users(id) ON DELETE SET NULL,
  vendedor_id               uuid REFERENCES users(id) ON DELETE SET NULL,
  agendado_por              uuid REFERENCES users(id) ON DELETE SET NULL,
  funil                     text CHECK (funil IN ('receptivo','prospeccao_ativa','outros')),
  qualificado               boolean,
  origem_mkt                text,
  urgencia_venda            text,
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
  data_agendamento          date,
  hora_agendamento          text,
  data_marcacao_agendamento date,
  compareceu_agendamento    boolean,
  data_compareceu           date,
  fechou_negocio            boolean,
  data_fechou_negocio       date,
  receita                   numeric(14,2),
  despesa                   numeric(14,2),
  rentabilidade             numeric(14,2),
  observacoes               text,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now()
)
""")
    op.execute('CREATE INDEX idx_leads_store         ON crm_funnel_leads (store_id)')
    op.execute('CREATE INDEX idx_leads_stage         ON crm_funnel_leads (stage_id)')
    op.execute('CREATE INDEX idx_leads_store_created ON crm_funnel_leads (store_id, created_at)')
    op.execute('CREATE INDEX idx_leads_assigned      ON crm_funnel_leads (assigned_to)')
    op.execute('CREATE INDEX idx_leads_vendedor      ON crm_funnel_leads (vendedor_id)')
    op.execute('CREATE INDEX idx_leads_telefone      ON crm_funnel_leads (store_id, telefone)')
    op.execute("""
CREATE TABLE crm_lead_stage_history (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id    uuid NOT NULL REFERENCES crm_funnel_leads(id) ON DELETE CASCADE,
  stage_id   uuid NOT NULL REFERENCES crm_funnel_stages(id) ON DELETE CASCADE,
  entered_at timestamptz NOT NULL DEFAULT now()
)
""")
    op.execute('CREATE INDEX idx_history_lead  ON crm_lead_stage_history (lead_id)')
    op.execute('CREATE INDEX idx_history_stage ON crm_lead_stage_history (stage_id)')
    op.execute("""
CREATE TABLE crm_stage_cooling_rules (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stage_id        uuid NOT NULL REFERENCES crm_funnel_stages(id) ON DELETE CASCADE,
  hours_threshold int NOT NULL,
  card_color      text NOT NULL DEFAULT '#facc15',
  message         text NOT NULL DEFAULT 'Lead esfriando',
  sort_order      int NOT NULL DEFAULT 0
)
""")
    op.execute('CREATE INDEX idx_cooling_stage ON crm_stage_cooling_rules (stage_id)')
    op.execute("""
CREATE TABLE crm_activity_log (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id      uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  action        text NOT NULL,
  entity_type   text,
  entity_id     uuid,
  payload       jsonb NOT NULL DEFAULT '{}',
  created_at    timestamptz NOT NULL DEFAULT now()
)
""")
    op.execute('CREATE INDEX idx_activity_store ON crm_activity_log (store_id, created_at)')
    op.execute("""
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
)
""")
    op.execute('CREATE INDEX idx_legacy_leads_store ON leads (store_id)')
    op.execute("""
CREATE TABLE daily_indicators (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id        uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  reference_date  date NOT NULL,
  origin          text NOT NULL CHECK (origin IN ('receptivo','prospeccao','outros')),
  origin_custom   text,
  total_leads     int NOT NULL DEFAULT 0,
  qualified_leads int NOT NULL DEFAULT 0,
  scheduled_leads int NOT NULL DEFAULT 0,
  attended_leads  int NOT NULL DEFAULT 0,
  converted_leads int NOT NULL DEFAULT 0,
  profitability   numeric(14,2),
  daily_expenses  numeric(14,2),
  notes           text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_id, reference_date, origin)
)
""")
    op.execute("""
CREATE TABLE goals (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id             uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  month                int NOT NULL CHECK (month BETWEEN 1 AND 12),
  year                 int NOT NULL,
  origin               text NOT NULL CHECK (origin IN ('receptivo','prospeccao','outros')),
  leads_quantity       int NOT NULL DEFAULT 0,
  qualified_quantity   int NOT NULL DEFAULT 0,
  scheduled_quantity   int NOT NULL DEFAULT 0,
  attended_quantity    int NOT NULL DEFAULT 0,
  conversions_quantity int NOT NULL DEFAULT 0,
  profitability_goal   numeric(14,2),
  average_ticket_goal  numeric(14,2),
  created_at           timestamptz NOT NULL DEFAULT now(),
  UNIQUE (store_id, year, month, origin)
)
""")
    op.execute("""
CREATE TABLE action_plans (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id    uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
  title       text NOT NULL,
  description text,
  status      text NOT NULL DEFAULT 'a_fazer' CHECK (status IN ('a_fazer','em_andamento','concluido')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
)
""")
    op.execute('CREATE INDEX idx_action_plans_store ON action_plans (store_id)')
    op.execute("""
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
)
""")
    op.execute("""
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
)
""")


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS bulk_send_contacts CASCADE')
    op.execute('DROP TABLE IF EXISTS bulk_sends CASCADE')
    op.execute('DROP TABLE IF EXISTS action_plans CASCADE')
    op.execute('DROP TABLE IF EXISTS goals CASCADE')
    op.execute('DROP TABLE IF EXISTS daily_indicators CASCADE')
    op.execute('DROP TABLE IF EXISTS leads CASCADE')
    op.execute('DROP TABLE IF EXISTS crm_activity_log CASCADE')
    op.execute('DROP TABLE IF EXISTS crm_stage_cooling_rules CASCADE')
    op.execute('DROP TABLE IF EXISTS crm_lead_stage_history CASCADE')
    op.execute('DROP TABLE IF EXISTS crm_funnel_leads CASCADE')
    op.execute('DROP TABLE IF EXISTS crm_funnel_stages CASCADE')
    op.execute('DROP TABLE IF EXISTS crm_funnels CASCADE')
    op.execute('DROP TABLE IF EXISTS user_store_access CASCADE')
    op.execute('ALTER TABLE stores DROP CONSTRAINT IF EXISTS fk_stores_last_assigned_sdr')
    op.execute('DROP TABLE IF EXISTS users CASCADE')
    op.execute('DROP TABLE IF EXISTS stores CASCADE')
