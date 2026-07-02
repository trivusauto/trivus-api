from datetime import date
from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range, build_monthly_series, last_month_keys
from src.modules.metrics.infrastructure.qualification_reader import QualificationReader
from src.modules.metrics.infrastructure.reader import MetricsLeadReader


class DashboardUseCase:
    def __init__(self, reader: MetricsLeadReader, qualification: QualificationReader) -> None:
        self._reader = reader
        self._qualification = qualification

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict[str, object]:
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._qualification.build(store_ids)
        totals = aggregate_totals_for_range(leads, start, end, ctx.passed)
        keys = last_month_keys(date.today(), 12)
        series = build_monthly_series(leads, keys, ctx.passed)
        return {"totals": totals, "monthly": [{"month": k, **series[k]} for k in keys]}
