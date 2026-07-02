from datetime import date
from src.modules.metrics.domain.metrics_core import aggregate_by_origin_for_range, build_monthly_series, last_month_keys
from src.modules.metrics.infrastructure.qualification_reader import QualificationReader
from src.modules.metrics.infrastructure.reader import MetricsLeadReader


class MarketingUseCase:
    def __init__(self, reader: MetricsLeadReader, qualification: QualificationReader) -> None:
        self._reader = reader
        self._qualification = qualification

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict[str, object]:
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._qualification.build(store_ids)
        by_origin = aggregate_by_origin_for_range(leads, start, end, ctx.passed)
        keys = last_month_keys(date.today(), 6)
        series = build_monthly_series(leads, keys, ctx.passed)
        chart = [
            {
                "month": k,
                "leads": series[k]["leads"],
                "conversions": series[k]["conversions"],
                "qualified": series[k]["qualified"],
                "scheduled": series[k]["scheduled"],
                "attended": series[k]["attended"],
            }
            for k in keys
        ]
        return {"byOrigin": by_origin, "chart": chart}
