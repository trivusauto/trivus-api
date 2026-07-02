from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class LegacyLeadModel(Base):
    __tablename__ = "leads"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    car: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    origin: Mapped[str | None] = mapped_column(String, nullable=True)
    origin_custom: Mapped[str | None] = mapped_column(String, nullable=True)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    qualified: Mapped[bool] = mapped_column(Boolean, default=False)
    disqualified: Mapped[bool] = mapped_column(Boolean, default=False)
    disqualification_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    attended: Mapped[bool] = mapped_column(Boolean, default=False)
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    profitability: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
