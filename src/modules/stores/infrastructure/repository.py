from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreAccessReader, StoreRepository, UserStoreAccessRepository
from src.modules.stores.infrastructure.orm import StoreModel, UserStoreAccessModel

_UPDATABLE = {"nome_fantasia", "razao_social", "cnpj", "crm_enabled", "zapi_webhook_enabled", "webhook_token", "active"}


def _to_domain(row: StoreModel) -> Store:
    return Store(
        id=str(row.id),
        nome_fantasia=row.nome_fantasia,
        razao_social=row.razao_social,
        cnpj=row.cnpj,
        crm_enabled=row.crm_enabled,
        zapi_webhook_enabled=row.zapi_webhook_enabled,
        webhook_token=row.webhook_token,
        active=row.active,
    )


class SqlAlchemyStoreRepository(StoreRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Store]:
        rows = (await self._session.execute(select(StoreModel).order_by(StoreModel.nome_fantasia))).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get_by_id(self, store_id: str) -> Store | None:
        row = await self._session.get(StoreModel, store_id)
        return _to_domain(row) if row else None

    async def create(self, data: dict[str, object]) -> Store:
        row = StoreModel(
            id=str(uuid4()),
            nome_fantasia=str(data["nome_fantasia"]),
            razao_social=str(data["razao_social"]) if data.get("razao_social") else None,
            cnpj=str(data["cnpj"]) if data.get("cnpj") else None,
            crm_enabled=bool(data.get("crm_enabled", False)),
            zapi_webhook_enabled=bool(data.get("zapi_webhook_enabled", False)),
            webhook_token=str(data["webhook_token"]) if data.get("webhook_token") else None,
            active=bool(data.get("active", True)),
        )
        self._session.add(row)
        await self._session.flush()
        return _to_domain(row)

    async def update(self, store_id: str, data: dict[str, object]) -> Store:
        row = await self._session.get(StoreModel, store_id)
        if row is None:
            from src.shared.domain.errors import NotFoundError
            raise NotFoundError(f"Store {store_id} not found")
        for key, value in data.items():
            if key in _UPDATABLE:
                setattr(row, key, value)
        await self._session.flush()
        return _to_domain(row)

    async def get_role_labels(self, store_id: str) -> object:
        row = await self._session.get(StoreModel, store_id)
        return row.shop_role_labels if row else None

    async def set_role_labels(self, store_id: str, labels: dict[str, str]) -> None:
        row = await self._session.get(StoreModel, store_id)
        if row is None:
            from src.shared.domain.errors import NotFoundError
            raise NotFoundError(f"Store {store_id} not found")
        row.shop_role_labels = labels  # type: ignore[assignment]
        await self._session.flush()


class SqlAlchemyStoreAccessReader(StoreAccessReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store_ids_for_user(self, user_id: str) -> list[str]:
        rows = (
            await self._session.execute(
                select(UserStoreAccessModel.store_id).where(UserStoreAccessModel.user_id == user_id)
            )
        ).scalars().all()
        return [str(r) for r in rows]


class SqlAlchemyUserStoreAccessRepository(UserStoreAccessRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_links(self, user_id: str, links: list[tuple[str, bool]]) -> None:
        await self._session.execute(
            delete(UserStoreAccessModel).where(UserStoreAccessModel.user_id == user_id)
        )
        for store_id, is_owner in links:
            self._session.add(
                UserStoreAccessModel(id=str(uuid4()), user_id=user_id, store_id=store_id, is_owner=is_owner)
            )
        await self._session.flush()
