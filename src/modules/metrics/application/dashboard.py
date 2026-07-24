from datetime import date

from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range, build_monthly_series, last_month_keys
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.metrics.infrastructure.stage_reach_reader import StageReachReader


class DashboardUseCase:
    def __init__(self, reader: MetricsLeadReader, stage_reach: StageReachReader) -> None:
        self._reader = reader
        self._stage_reach = stage_reach

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict[str, object]:
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        classified_ctx = await self._stage_reach.build(store_ids, "CLASSIFICADOS")
        totals = aggregate_totals_for_range(leads, start, end, ctx.passed, classified_ctx.passed)
        keys = last_month_keys(date.today(), 12)
        series = build_monthly_series(leads, keys, ctx.passed)
        return {"totals": totals, "monthly": [{"month": k, **series[k]} for k in keys]}
