from sqlalchemy import Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class GoalModel(Base):
    __tablename__ = "goals"
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String)
    leads_quantity: Mapped[int] = mapped_column(Integer, default=0)
    classified_quantity: Mapped[int] = mapped_column(Integer, default=0)
    qualified_quantity: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_quantity: Mapped[int] = mapped_column(Integer, default=0)
    attended_quantity: Mapped[int] = mapped_column(Integer, default=0)
    conversions_quantity: Mapped[int] = mapped_column(Integer, default=0)
    profitability_goal: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    average_ticket_goal: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    marketing_investment_goal: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
