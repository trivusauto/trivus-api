"""add data_comprado to crm_funnel_leads

Revision ID: b7e2f4a91c03
Revises: a0b13c39f141
Create Date: 2026-07-16

Data em que o veículo foi comprado (coluna VEICULOS COMPRADOS do funil).
Auto-preenchida ao mover o lead para a coluna; editável para lançamentos
retroativos (comprou em junho, registrou depois).
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'b7e2f4a91c03'
down_revision: Union[str, Sequence[str], None] = 'a0b13c39f141'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE crm_funnel_leads ADD COLUMN IF NOT EXISTS data_comprado date")


def downgrade() -> None:
    op.execute("ALTER TABLE crm_funnel_leads DROP COLUMN IF EXISTS data_comprado")
