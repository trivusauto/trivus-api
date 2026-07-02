import uuid
from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.action_plans.infrastructure.orm import ActionPlanModel


def _to_dict(r: ActionPlanModel) -> dict[str, object]:
    d: dict[str, object] = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["id"] = str(d["id"])
    for k in ("created_at", "updated_at"):
        v = d.get(k)
        if v is not None:
            d[k] = str(v.isoformat())  # type: ignore[attr-defined]
    return d


class ActionPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_store(self, store_id: str) -> list[dict[str, object]]:
        rows = (await self._session.execute(
            select(ActionPlanModel).where(ActionPlanModel.store_id == store_id).order_by(ActionPlanModel.created_at.desc())
        )).scalars().all()
        return [_to_dict(r) for r in rows]

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        row = ActionPlanModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return _to_dict(row)

    async def update(self, plan_id: str, data: dict[str, object]) -> dict[str, object]:
        row = await self._session.get(ActionPlanModel, plan_id)
        if row is None:
            raise ValueError(f"ActionPlan {plan_id} not found")
        for k, v in data.items():
            setattr(row, k, v)
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return _to_dict(row)

    async def delete(self, plan_id: str) -> None:
        await self._session.execute(delete(ActionPlanModel).where(ActionPlanModel.id == plan_id))
