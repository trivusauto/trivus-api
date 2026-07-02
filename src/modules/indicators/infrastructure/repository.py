import uuid
from datetime import date
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.indicators.infrastructure.orm import DailyIndicatorModel


def _to_dict(r: DailyIndicatorModel) -> dict[str, object]:
    d: dict[str, object] = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["id"] = str(d["id"])
    d["reference_date"] = str(d["reference_date"].isoformat())  # type: ignore[attr-defined]
    if d.get("created_at") is not None:
        d["created_at"] = str(d["created_at"].isoformat())  # type: ignore[attr-defined]
    for k in ("profitability", "daily_expenses"):
        if d.get(k) is not None:
            d[k] = float(d[k])  # type: ignore[arg-type]
    return d


class IndicatorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, store_id: str, date_from: str | None, date_to: str | None) -> list[dict[str, object]]:
        stmt = select(DailyIndicatorModel).where(DailyIndicatorModel.store_id == store_id)
        if date_from:
            stmt = stmt.where(DailyIndicatorModel.reference_date >= date.fromisoformat(date_from))
        if date_to:
            stmt = stmt.where(DailyIndicatorModel.reference_date <= date.fromisoformat(date_to))
        rows = (await self._session.execute(stmt.order_by(DailyIndicatorModel.reference_date.desc()))).scalars().all()
        return [_to_dict(r) for r in rows]

    async def upsert(self, data: dict[str, object]) -> None:
        values: dict[str, object] = {**data, "id": str(uuid.uuid4()), "reference_date": date.fromisoformat(str(data["reference_date"]))}
        stmt = pg_insert(DailyIndicatorModel).values(**values)
        update_cols = {k: v for k, v in values.items() if k not in ("id", "store_id", "reference_date", "origin", "created_at")}
        stmt = stmt.on_conflict_do_update(index_elements=["store_id", "reference_date", "origin"], set_=update_cols)
        await self._session.execute(stmt)
