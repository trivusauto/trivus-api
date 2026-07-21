"""add meta ads integration (campaign daily spend + meta ids)

Revision ID: c7f4b2e918d5
Revises: b7e2f4a91c03
Create Date: 2026-07-21

Integração com a Meta Ads (Marketing API): gasto diário por campanha em
`campaign_daily_spend`, `meta_campaign_id` nas campanhas e `meta_ad_account_id`
nas lojas. Automatiza o investimento de marketing que antes era digitado à mão.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c7f4b2e918d5'
down_revision: Union[str, Sequence[str], None] = 'b7e2f4a91c03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE marketing_campaigns ADD COLUMN IF NOT EXISTS meta_campaign_id text")
    op.execute("ALTER TABLE stores ADD COLUMN IF NOT EXISTS meta_ad_account_id text")
    op.execute("""
        CREATE TABLE IF NOT EXISTS campaign_daily_spend (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            store_id uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
            campaign_id uuid REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
            reference_date date NOT NULL,
            spend numeric(14,2) NOT NULL DEFAULT 0,
            impressions int,
            clicks int,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (campaign_id, reference_date)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_campaign_daily_spend_store_date "
        "ON campaign_daily_spend (store_id, reference_date)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS campaign_daily_spend")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS meta_ad_account_id")
    op.execute("ALTER TABLE marketing_campaigns DROP COLUMN IF EXISTS meta_campaign_id")
