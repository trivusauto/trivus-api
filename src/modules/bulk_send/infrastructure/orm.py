from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class BulkSendModel(Base):
    __tablename__ = "bulk_sends"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    total_contacts: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="draft")
    message_template: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_1: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_2: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_3: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_4: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_5: Mapped[str | None] = mapped_column(String, nullable=True)
    delay_min_sec: Mapped[int] = mapped_column(Integer, default=30)
    delay_max_sec: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BulkSendContactModel(Base):
    __tablename__ = "bulk_send_contacts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    bulk_send_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    phone: Mapped[str] = mapped_column(String)
    variation_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
