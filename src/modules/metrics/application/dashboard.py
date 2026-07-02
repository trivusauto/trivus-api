from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range
from src.modules.metrics.infrastructure.reader import MetricsLeadReader


class DashboardUseCase:
    def __init__(self, reader: MetricsLeadReader) -> None:
        self._reader = reader

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict[str, object]:
        return aggregate_totals_for_range(await self._reader.leads_for_stores(store_ids), start, end)
