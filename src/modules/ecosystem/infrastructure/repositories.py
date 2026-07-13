import uuid
from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.ecosystem.infrastructure.orm import (
    CompanyModel, PlanModel, ServiceInterestModel, ServiceModel,
    StoreServiceModel, SubscriptionModel, SubscriptionPaymentModel,
)
from src.shared.domain.errors import NotFoundError
from src.shared.infrastructure.database import Base


def _row_to_dict(row: object) -> dict[str, object]:
    d: dict[str, object] = {c.name: getattr(row, c.name) for c in row.__table__.columns}  # type: ignore[attr-defined]
    for k, v in list(d.items()):
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
        elif (k == "id" or k.endswith("_id")) and v is not None:
            d[k] = str(v)
        elif k in ("price_month", "amount", "budget") and v is not None:
            d[k] = float(v)  # type: ignore[arg-type]
    return d


class _CrudRepo:
    model: ClassVar[type[Base]]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, obj_id: str) -> dict[str, object] | None:
        row = await self._session.get(self.model, obj_id)
        return _row_to_dict(row) if row else None

    async def get_or_raise(self, obj_id: str) -> dict[str, object]:
        d = await self.get(obj_id)
        if d is None:
            raise NotFoundError(f"{getattr(self.model, '__tablename__', self.model.__name__)}: não encontrado")
        return d

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        row = self.model(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return _row_to_dict(row)

    async def update(self, obj_id: str, data: dict[str, object]) -> dict[str, object]:
        row = await self._session.get(self.model, obj_id)
        if row is None:
            raise NotFoundError(f"{getattr(self.model, '__tablename__', self.model.__name__)}: não encontrado")
        for k, v in data.items():
            setattr(row, k, v)
        await self._session.flush()
        return _row_to_dict(row)


class CompanyRepository(_CrudRepo):
    model = CompanyModel

    async def list_all(self) -> list[dict[str, object]]:
        rows = (await self._session.execute(select(CompanyModel).order_by(CompanyModel.name))).scalars().all()
        return [_row_to_dict(r) for r in rows]


class PlanRepository(_CrudRepo):
    model = PlanModel

    async def list_all(self) -> list[dict[str, object]]:
        rows = (await self._session.execute(select(PlanModel).order_by(PlanModel.name))).scalars().all()
        return [_row_to_dict(r) for r in rows]

    async def get_by_key(self, key: str) -> dict[str, object] | None:
        row = (await self._session.execute(select(PlanModel).where(PlanModel.key == key))).scalar_one_or_none()
        return _row_to_dict(row) if row else None


class SubscriptionRepository(_CrudRepo):
    model = SubscriptionModel

    async def current_for_company(self, company_id: str) -> dict[str, object] | None:
        stmt = (select(SubscriptionModel)
                .where(SubscriptionModel.company_id == company_id, SubscriptionModel.status != "canceled")
                .order_by(SubscriptionModel.created_at.desc()).limit(1))
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _row_to_dict(row) if row else None

    async def list_all(self) -> list[dict[str, object]]:
        rows = (await self._session.execute(
            select(SubscriptionModel).order_by(SubscriptionModel.created_at.desc())
        )).scalars().all()
        return [_row_to_dict(r) for r in rows]


class ServiceRepository(_CrudRepo):
    model = ServiceModel

    async def list_all(self, only_active: bool = False) -> list[dict[str, object]]:
        stmt = select(ServiceModel).order_by(ServiceModel.sort_order, ServiceModel.name)
        if only_active:
            stmt = stmt.where(ServiceModel.active.is_(True))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_row_to_dict(r) for r in rows]

    async def get_by_key(self, key: str) -> dict[str, object] | None:
        row = (await self._session.execute(select(ServiceModel).where(ServiceModel.key == key))).scalar_one_or_none()
        return _row_to_dict(row) if row else None


class StoreServiceRepository(_CrudRepo):
    model = StoreServiceModel

    async def enabled_keys_for_store(self, store_id: str) -> list[str]:
        stmt = select(StoreServiceModel.service_key).where(
            StoreServiceModel.store_id == store_id, StoreServiceModel.enabled.is_(True)
        )
        return [str(k) for k in (await self._session.execute(stmt)).scalars().all()]

    async def set_service(self, store_id: str, service_key: str, enabled: bool) -> None:
        stmt = select(StoreServiceModel).where(StoreServiceModel.store_id == store_id,
                                               StoreServiceModel.service_key == service_key)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            self._session.add(StoreServiceModel(id=str(uuid.uuid4()), store_id=store_id,
                                                service_key=service_key, enabled=enabled))
        else:
            row.enabled = enabled
        await self._session.flush()


class ServiceInterestRepository(_CrudRepo):
    model = ServiceInterestModel

    async def list_by_status(self, status: str | None) -> list[dict[str, object]]:
        stmt = select(ServiceInterestModel).order_by(ServiceInterestModel.created_at.desc())
        if status:
            stmt = stmt.where(ServiceInterestModel.status == status)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_row_to_dict(r) for r in rows]


class SubscriptionPaymentRepository(_CrudRepo):
    model = SubscriptionPaymentModel
