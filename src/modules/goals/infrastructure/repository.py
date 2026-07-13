import uuid
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.goals.infrastructure.orm import GoalModel


def _to_dict(r: GoalModel) -> dict[str, object]:
    d: dict[str, object] = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["id"] = str(d["id"])
    for k in ("profitability_goal", "average_ticket_goal", "marketing_investment_goal"):
        if d.get(k) is not None:
            d[k] = float(d[k])  # type: ignore[arg-type]
    return d


class GoalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, store_id: str, year: int, month: int) -> list[dict[str, object]]:
        rows = (await self._session.execute(
            select(GoalModel).where(GoalModel.store_id == store_id, GoalModel.year == year, GoalModel.month == month)
        )).scalars().all()
        return [_to_dict(r) for r in rows]

    async def upsert(self, data: dict[str, object]) -> dict[str, object]:
        values: dict[str, object] = {**data, "id": str(uuid.uuid4())}
        stmt = pg_insert(GoalModel).values(**values)
        update_cols = {k: v for k, v in values.items() if k not in ("id", "store_id", "year", "month", "origin")}
        stmt = stmt.on_conflict_do_update(index_elements=["store_id", "year", "month", "origin"], set_=update_cols)
        await self._session.execute(stmt)
        rows = (await self._session.execute(
            select(GoalModel).where(
                GoalModel.store_id == str(data["store_id"]),
                GoalModel.year == int(data["year"]),  # type: ignore[call-overload]
                GoalModel.month == int(data["month"]),  # type: ignore[call-overload]
                GoalModel.origin == str(data["origin"]),
            )
        )).scalar_one()
        return _to_dict(rows)

    async def delete(self, goal_id: str) -> None:
        await self._session.execute(delete(GoalModel).where(GoalModel.id == goal_id))
