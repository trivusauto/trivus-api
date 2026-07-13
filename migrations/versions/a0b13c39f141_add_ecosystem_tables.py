"""add ecosystem tables

Revision ID: a0b13c39f141
Revises: c21ee08cf155
Create Date: 2026-07-12 22:39:49.612814

Ecossistema da holding (spec ECOSSISTEMA_TRIVUS.md / MODELO_ALVO §17-23):
empresas, planos, assinaturas, catálogo de serviços (CRUD), serviços por loja,
interesses (upsell) e eventos de pagamento do framework de cobrança.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a0b13c39f141'
down_revision: Union[str, Sequence[str], None] = 'c21ee08cf155'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE companies (
          id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          name             text NOT NULL,
          cnpj             text,
          responsible_name text,
          active           boolean NOT NULL DEFAULT true,
          created_at       timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        ALTER TABLE stores
        ADD COLUMN company_id uuid REFERENCES companies(id) ON DELETE RESTRICT
    """)
    op.execute("""
        CREATE TABLE plans (
          id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          key          text NOT NULL UNIQUE,
          name         text NOT NULL,
          service_keys jsonb NOT NULL DEFAULT '[]',
          max_stores   int,
          price_month  numeric(14,2),
          active       boolean NOT NULL DEFAULT true,
          created_at   timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE subscriptions (
          id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id              uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
          plan_id                 uuid NOT NULL REFERENCES plans(id),
          status                  text NOT NULL CHECK (status IN ('trialing','active','suspended','canceled')),
          trial_ends_at           date,
          billing_mode            text NOT NULL DEFAULT 'manual' CHECK (billing_mode IN ('manual','gateway')),
          gateway_customer_id     text,
          gateway_subscription_id text,
          started_at              date,
          canceled_at             date,
          notes                   text,
          created_at              timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_subscriptions_company ON subscriptions (company_id)")
    op.execute("""
        CREATE TABLE services (
          id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          key          text NOT NULL UNIQUE,
          name         text NOT NULL,
          type         text NOT NULL CHECK (type IN ('software','humano')),
          what_it_is   text,
          what_it_does text,
          upsell_pitch text,
          feature_keys jsonb NOT NULL DEFAULT '[]',
          sort_order   int NOT NULL DEFAULT 0,
          active       boolean NOT NULL DEFAULT true,
          created_at   timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE store_services (
          id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          store_id    uuid NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
          service_key text NOT NULL REFERENCES services(key),
          enabled     boolean NOT NULL DEFAULT true,
          UNIQUE (store_id, service_key)
        )
    """)
    op.execute("""
        CREATE TABLE service_interests (
          id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id   uuid REFERENCES companies(id) ON DELETE SET NULL,
          store_id     uuid REFERENCES stores(id) ON DELETE SET NULL,
          service_key  text NOT NULL REFERENCES services(key),
          requested_by uuid REFERENCES users(id) ON DELETE SET NULL,
          status       text NOT NULL DEFAULT 'novo' CHECK (status IN ('novo','contatado','convertido','descartado')),
          notes        text,
          created_at   timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_interests_status ON service_interests (status, created_at)")
    op.execute("""
        CREATE TABLE subscription_payments (
          id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          subscription_id uuid NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
          external_id     text,
          gateway         text,
          event_type      text NOT NULL,
          status          text NOT NULL,
          amount          numeric(14,2),
          paid_at         timestamptz,
          payload         jsonb NOT NULL DEFAULT '{}',
          created_at      timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_subpay_sub ON subscription_payments (subscription_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subscription_payments")
    op.execute("DROP TABLE IF EXISTS service_interests")
    op.execute("DROP TABLE IF EXISTS store_services")
    op.execute("DROP TABLE IF EXISTS services")
    op.execute("DROP TABLE IF EXISTS subscriptions")
    op.execute("DROP TABLE IF EXISTS plans")
    op.execute("ALTER TABLE stores DROP COLUMN IF EXISTS company_id")
    op.execute("DROP TABLE IF EXISTS companies")
