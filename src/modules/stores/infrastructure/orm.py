from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class StoreModel(Base):
    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    nome_fantasia: Mapped[str] = mapped_column(String)
    razao_social: Mapped[str | None] = mapped_column(String, nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String, nullable=True)
    crm_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    zapi_webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_token: Mapped[str | None] = mapped_column(String, nullable=True)
    shop_role_labels: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_assigned_sdr_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class UserStoreAccessModel(Base):
    __tablename__ = "user_store_access"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)
