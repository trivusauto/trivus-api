"""add marketing campaigns and fields

Revision ID: c21ee08cf155
Revises: d786a5d623c4
Create Date: 2026-07-12 22:21:56.174894

Módulo Marketing (spec MUDANCAS_MARKETING_RELATORIOS.md / MODELO_ALVO §16):
campanhas como entidade, vínculo campanha↔lead, flag de obrigatoriedade na loja,
meta de investimento e lançamentos diários de investimento/classificados.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c21ee08cf155'
down_revision: Union[str, Sequence[str], None] = 'd786a5d623c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE marketing_campaigns (
          id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          store_id   uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
          name       text NOT NULL,
          link_code  text,
          started_at date NOT NULL,
          ended_at   date,
          budget     numeric(14,2),
          created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_campaigns_store ON marketing_campaigns (store_id)")
    op.execute("""
        ALTER TABLE crm_funnel_leads
        ADD COLUMN campaign_id uuid REFERENCES marketing_campaigns(id) ON DELETE SET NULL
    """)
    op.execute("CREATE INDEX idx_leads_campaign ON crm_funnel_leads (campaign_id)")
    op.execute("ALTER TABLE stores ADD COLUMN require_campaign_on_lead boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE goals ADD COLUMN marketing_investment_goal numeric(14,2)")
    op.execute("ALTER TABLE daily_indicators ADD COLUMN classified_leads int NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE daily_indicators ADD COLUMN marketing_investment numeric(14,2)")


def downgrade() -> None:
    op.execute("ALTER TABLE daily_indicators DROP COLUMN IF EXISTS marketing_investment")
    op.execute("ALTER TABLE daily_indicators DROP COLUMN IF EXISTS classified_leads")
    op.execute("ALTER TABLE goals DROP COLUMN IF EXISTS marketing_investment_goal")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS require_campaign_on_lead")
    op.execute("DROP INDEX IF EXISTS idx_leads_campaign")
    op.execute("ALTER TABLE crm_funnel_leads DROP COLUMN IF EXISTS campaign_id")
    op.execute("DROP TABLE IF EXISTS marketing_campaigns")
