from src.modules.metrics.domain.metrics_core import build_report_processed
from src.modules.metrics.infrastructure.reader import MetricsLeadReader


class ReportUseCase:
    def __init__(self, reader: MetricsLeadReader) -> None:
        self._reader = reader

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict[str, object]:
        return build_report_processed(await self._reader.leads_for_stores(store_ids), start, end)
