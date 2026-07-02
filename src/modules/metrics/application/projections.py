from calendar import monthrange
from datetime import date

from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range
from src.modules.metrics.domain.working_days import WorkingDays
from src.modules.metrics.infrastructure.reader import MetricsLeadReader


class ProjectionsUseCase:
    def __init__(self, reader: MetricsLeadReader, workdays: WorkingDays) -> None:
        self._reader = reader
        self._workdays = workdays

    async def execute(self, store_ids: list[str], year: int, month: int) -> dict[str, object]:
        last = monthrange(year, month)[1]
        start, end = f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"
        totals = aggregate_totals_for_range(await self._reader.leads_for_stores(store_ids), start, end)
        today = date.today()
        current_day = today.day if (today.year, today.month) == (year, month) else last
        total_wd = self._workdays.working_days_in_month(year, month)
        remaining = self._workdays.remaining_working_days(year, month, current_day)
        elapsed = total_wd - remaining
        conversions = int(totals["conversions"])  # type: ignore[call-overload]
        pace = conversions / elapsed if elapsed > 0 else 0.0
        return {
            "totals": totals,
            "working_days": {"elapsed": elapsed, "remaining": remaining},
            "projected_conversions": round(conversions + pace * remaining),
        }
