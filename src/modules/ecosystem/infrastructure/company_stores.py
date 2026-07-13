from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.stores.infrastructure.orm import StoreModel


class CompanyStoresReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_stores(self, company_id: str) -> int:
        stmt = select(func.count()).select_from(StoreModel).where(StoreModel.company_id == company_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def store_company(self, store_id: str) -> str | None:
        row = await self._session.get(StoreModel, store_id)
        return str(row.company_id) if row and row.company_id else None
