from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class CampaignDailySpendModel(Base):
    __tablename__ = "campaign_daily_spend"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    campaign_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    reference_date: Mapped[date] = mapped_column(Date)
    spend: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
