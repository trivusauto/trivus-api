from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.stores.infrastructure.orm import StoreModel


class StoreFlagsReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def require_campaign(self, store_id: str) -> bool:
        row = await self._session.get(StoreModel, store_id)
        return bool(row and row.require_campaign_on_lead)
