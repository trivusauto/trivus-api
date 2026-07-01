"""add_last_assigned_sdr_id_to_stores

Revision ID: d786a5d623c4
Revises: cc333adabd6f
Create Date: 2026-07-01 20:08:30.939563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd786a5d623c4'
down_revision: Union[str, Sequence[str], None] = 'cc333adabd6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('stores', sa.Column('last_assigned_sdr_id', postgresql.UUID(), nullable=True))


def downgrade() -> None:
    op.drop_column('stores', 'last_assigned_sdr_id')
