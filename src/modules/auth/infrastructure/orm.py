from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String)
    parent_store_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    shop_role: Mapped[str | None] = mapped_column(String, nullable=True)
    menu_permissions: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    can_see_unassigned_leads: Mapped[bool] = mapped_column(Boolean, default=False)
