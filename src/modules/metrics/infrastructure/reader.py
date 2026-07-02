from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.infrastructure.orm import LeadModel
from src.modules.crm.infrastructure.repositories import lead_to_dict


class MetricsLeadReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def leads_for_stores(self, store_ids: list[str]) -> list[dict[str, object]]:
        if not store_ids:
            return []
        rows = (await self._session.execute(select(LeadModel).where(LeadModel.store_id.in_(store_ids)))).scalars().all()
        return [lead_to_dict(r) for r in rows]
