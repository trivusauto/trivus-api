"""add can_edit_others_leads to users

Revision ID: f3b8d0c47a92
Revises: e1a7c4d92b60
Create Date: 2026-07-24

Autorização para editar leads de OUTROS colaboradores. Default false: a permissão
é concedida por admin/dono/gerente, nunca retirada (decisão do cliente 23/07).
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'f3b8d0c47a92'
down_revision: Union[str, Sequence[str], None] = 'e1a7c4d92b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "can_edit_others_leads boolean NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS can_edit_others_leads")
