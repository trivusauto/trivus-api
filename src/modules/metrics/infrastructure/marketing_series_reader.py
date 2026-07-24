"""Série DIÁRIA de marketing (S4.4): uma linha por dia do período.

Fonte: `daily_indicators` agregado por data (uma query com GROUP BY — sem N+1).
O investimento segue a mesma preferência do `InvestmentReader` usado pelo funil de
custos: gasto sincronizado da Meta quando existe, senão o lançamento diário.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.indicators.infrastructure.orm import DailyIndicatorModel
from src.modules.integrations.meta.infrastructure.orm import CampaignDailySpendModel

DayRow = dict[str, object]

_NUMERIC_KEYS = (
    "leads", "classificados", "qualificados", "agendados", "comparecidos", "vendas", "investimento",
)


class MarketingSeriesReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def days(self, store_ids: list[str], start: str, end: str) -> list[DayRow]:
        """Uma linha por dia COM movimento, ordenada por data."""
        if not store_ids:
            return []

        d = DailyIndicatorModel
        stmt = (
            select(
                d.reference_date,
                func.coalesce(func.sum(d.total_leads), 0),
                func.coalesce(func.sum(d.classified_leads), 0),
                func.coalesce(func.sum(d.qualified_leads), 0),
                func.coalesce(func.sum(d.scheduled_leads), 0),
                func.coalesce(func.sum(d.attended_leads), 0),
                func.coalesce(func.sum(d.converted_leads), 0),
                func.coalesce(func.sum(d.marketing_investment), 0),
            )
            .where(
                d.store_id.in_(store_ids),
                d.reference_date >= date.fromisoformat(start),
                d.reference_date <= date.fromisoformat(end),
            )
            .group_by(d.reference_date)
            .order_by(d.reference_date)
        )
        rows = (await self._session.execute(stmt)).all()
        meta_by_day = await self._meta_spend_by_day(store_ids, start, end)

        return [
            {
                "date": ref.isoformat(),
                "leads": int(leads),
                "classificados": int(classificados),
                "qualificados": int(qualificados),
                "agendados": int(agendados),
                "comparecidos": int(comparecidos),
                "vendas": int(vendas),
                # Meta tem prioridade no dia em que houver gasto sincronizado.
                "investimento": float(meta_by_day.get(ref, float(investimento or 0))),
            }
            for ref, leads, classificados, qualificados, agendados, comparecidos, vendas, investimento in rows
        ]

    async def _meta_spend_by_day(
        self, store_ids: list[str], start: str, end: str
    ) -> dict[date, float]:
        c = CampaignDailySpendModel
        stmt = (
            select(c.reference_date, func.coalesce(func.sum(c.spend), 0))
            .where(
                c.store_id.in_(store_ids),
                c.reference_date >= date.fromisoformat(start),
                c.reference_date <= date.fromisoformat(end),
            )
            .group_by(c.reference_date)
        )
        return {ref: float(spend or 0) for ref, spend in (await self._session.execute(stmt)).all()}


def totals_of(days: list[DayRow]) -> dict[str, float]:
    """Soma dos dias — as chaves numéricas do bloco."""
    return {k: sum(float(cast_num(d[k])) for d in days) for k in _NUMERIC_KEYS}


def cast_num(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def previous_window(start: str, end: str) -> tuple[str, str]:
    """Janela imediatamente anterior, de mesma duração (comparativo dos KPI cards)."""
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    span = (e - s).days + 1
    prev_end = s - timedelta(days=1)
    return (prev_end - timedelta(days=span - 1)).isoformat(), prev_end.isoformat()
