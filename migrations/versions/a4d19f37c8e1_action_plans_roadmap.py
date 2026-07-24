"""action plans: prazo, responsáveis e etapas

Revision ID: a4d19f37c8e1
Revises: f3b8d0c47a92
Create Date: 2026-07-24

Transforma o plano de ação num mini-roadmap: data limite, responsáveis (lista de
user_ids) e etapas com prazo próprio. As etapas caem junto com o plano (CASCADE).
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a4d19f37c8e1'
down_revision: Union[str, Sequence[str], None] = 'f3b8d0c47a92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE action_plans ADD COLUMN IF NOT EXISTS due_date date")
    op.execute("ALTER TABLE action_plans ADD COLUMN IF NOT EXISTS responsible_ids jsonb")
    op.execute("""
        CREATE TABLE IF NOT EXISTS action_plan_steps (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            plan_id uuid NOT NULL REFERENCES action_plans(id) ON DELETE CASCADE,
            title text NOT NULL,
            description text,
            due_date date,
            done boolean NOT NULL DEFAULT false,
            sort_order int NOT NULL DEFAULT 0
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_action_plan_steps_plan ON action_plan_steps (plan_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS action_plan_steps")
    op.execute("ALTER TABLE action_plans DROP COLUMN IF EXISTS responsible_ids")
    op.execute("ALTER TABLE action_plans DROP COLUMN IF EXISTS due_date")
