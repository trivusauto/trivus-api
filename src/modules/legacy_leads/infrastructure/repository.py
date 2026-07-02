import uuid
from datetime import date, datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.legacy_leads.infrastructure.orm import LegacyLeadModel


def _to_dict(r: LegacyLeadModel) -> dict[str, object]:
    d: dict[str, object] = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["id"] = str(d["id"])
    for k in ("entry_date", "created_at", "updated_at"):
        v = d.get(k)
        if v is not None:
            d[k] = str(v.isoformat())  # type: ignore[attr-defined]
    if d.get("profitability") is not None:
        d["profitability"] = float(d["profitability"])  # type: ignore[arg-type]
    return d


class LegacyLeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_store(self, store_id: str) -> list[dict[str, object]]:
        rows = (await self._session.execute(
            select(LegacyLeadModel).where(LegacyLeadModel.store_id == store_id).order_by(LegacyLeadModel.created_at.desc())
        )).scalars().all()
        return [_to_dict(r) for r in rows]

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        if data.get("entry_date"):
            data = {**data, "entry_date": date.fromisoformat(str(data["entry_date"]))}
        row = LegacyLeadModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return _to_dict(row)

    async def update(self, lead_id: str, data: dict[str, object]) -> dict[str, object]:
        row = await self._session.get(LegacyLeadModel, lead_id)
        if row is None:
            raise ValueError(f"Lead {lead_id} not found")
        for k, v in data.items():
            setattr(row, k, v)
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return _to_dict(row)

    async def delete(self, lead_id: str) -> None:
        await self._session.execute(delete(LegacyLeadModel).where(LegacyLeadModel.id == lead_id))
