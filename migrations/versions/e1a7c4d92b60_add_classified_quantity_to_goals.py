"""add classified_quantity to goals

Revision ID: e1a7c4d92b60
Revises: c7f4b2e918d5
Create Date: 2026-07-24

Meta de leads CLASSIFICADOS por origem. O realizado já existe em
`daily_indicators.classified_leads`; faltava a meta correspondente.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'e1a7c4d92b60'
down_revision: Union[str, Sequence[str], None] = 'c7f4b2e918d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE goals ADD COLUMN IF NOT EXISTS classified_quantity int")


def downgrade() -> None:
    op.execute("ALTER TABLE goals DROP COLUMN IF EXISTS classified_quantity")
