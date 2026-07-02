from datetime import datetime
from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class ActionPlanModel(Base):
    __tablename__ = "action_plans"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="a_fazer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
