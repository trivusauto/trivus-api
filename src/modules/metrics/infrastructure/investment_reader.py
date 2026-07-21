from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.indicators.infrastructure.orm import DailyIndicatorModel
from src.modules.integrations.meta.infrastructure.orm import CampaignDailySpendModel


class InvestmentReader:
    """Investimento realizado do período.

    Preferência: gasto sincronizado da Meta Ads (`campaign_daily_spend`) quando há
    linhas no período — integração Meta ativa para a loja. Fallback: soma dos
    lançamentos diários `daily_indicators.marketing_investment` (decisão D2 da spec
    de marketing). Lojas sem Meta continuam idênticas (backward-compatible)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total(self, store_ids: list[str], start: str, end: str) -> float:
        if not store_ids:
            return 0.0
        meta_spend = await self._meta_spend(store_ids, start, end)
        if meta_spend is not None:
            return meta_spend
        return await self._daily_indicators_total(store_ids, start, end)

    async def _meta_spend(self, store_ids: list[str], start: str, end: str) -> float | None:
        """SUM(spend) quando há linhas Meta no período; None se não houver (usa fallback)."""
        stmt = select(
            func.coalesce(func.sum(CampaignDailySpendModel.spend), 0),
            func.count(),
        ).where(
            CampaignDailySpendModel.store_id.in_(store_ids),
            CampaignDailySpendModel.reference_date >= date.fromisoformat(start),
            CampaignDailySpendModel.reference_date <= date.fromisoformat(end),
        )
        total, count = (await self._session.execute(stmt)).one()
        return float(total or 0) if count else None

    async def _daily_indicators_total(self, store_ids: list[str], start: str, end: str) -> float:
        stmt = select(func.coalesce(func.sum(DailyIndicatorModel.marketing_investment), 0)).where(
            DailyIndicatorModel.store_id.in_(store_ids),
            DailyIndicatorModel.reference_date >= date.fromisoformat(start),
            DailyIndicatorModel.reference_date <= date.fromisoformat(end),
        )
        total = (await self._session.execute(stmt)).scalar_one()
        return float(total or 0)
