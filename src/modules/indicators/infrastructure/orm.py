from datetime import date, datetime
from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class DailyIndicatorModel(Base):
    __tablename__ = "daily_indicators"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    reference_date: Mapped[date] = mapped_column(Date)
    origin: Mapped[str] = mapped_column(String)
    origin_custom: Mapped[str | None] = mapped_column(String, nullable=True)
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    qualified_leads: Mapped[int] = mapped_column(Integer, default=0)
    classified_leads: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_leads: Mapped[int] = mapped_column(Integer, default=0)
    attended_leads: Mapped[int] = mapped_column(Integer, default=0)
    converted_leads: Mapped[int] = mapped_column(Integer, default=0)
    profitability: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    daily_expenses: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    marketing_investment: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
