from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.indicators.infrastructure.orm import DailyIndicatorModel


class InvestmentReader:
    """Investimento realizado do período = soma dos lançamentos diários
    `daily_indicators.marketing_investment` (decisão D2 da spec de marketing)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total(self, store_ids: list[str], start: str, end: str) -> float:
        if not store_ids:
            return 0.0
        stmt = select(func.coalesce(func.sum(DailyIndicatorModel.marketing_investment), 0)).where(
            DailyIndicatorModel.store_id.in_(store_ids),
            DailyIndicatorModel.reference_date >= date.fromisoformat(start),
            DailyIndicatorModel.reference_date <= date.fromisoformat(end),
        )
        total = (await self._session.execute(stmt)).scalar_one()
        return float(total or 0)
