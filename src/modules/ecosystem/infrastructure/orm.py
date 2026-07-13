from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class CompanyModel(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    name: Mapped[str] = mapped_column(String)
    cnpj: Mapped[str | None] = mapped_column(String, nullable=True)
    responsible_name: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlanModel(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    service_keys: Mapped[list[str]] = mapped_column(JSONB, default=list)
    max_stores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_month: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    company_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    plan_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    status: Mapped[str] = mapped_column(String)
    trial_ends_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_mode: Mapped[str] = mapped_column(String, default="manual")
    gateway_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    gateway_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    canceled_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceModel(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    what_it_is: Mapped[str | None] = mapped_column(String, nullable=True)
    what_it_does: Mapped[str | None] = mapped_column(String, nullable=True)
    upsell_pitch: Mapped[str | None] = mapped_column(String, nullable=True)
    feature_keys: Mapped[list[str]] = mapped_column(JSONB, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoreServiceModel(Base):
    __tablename__ = "store_services"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    service_key: Mapped[str] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ServiceInterestModel(Base):
    __tablename__ = "service_interests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    company_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    store_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    service_key: Mapped[str] = mapped_column(String)
    requested_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    status: Mapped[str] = mapped_column(String, default="novo")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubscriptionPaymentModel(Base):
    __tablename__ = "subscription_payments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    gateway: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
