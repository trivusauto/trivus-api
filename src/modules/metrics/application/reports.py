from src.modules.metrics.domain.metrics_core import build_report_processed
from src.modules.metrics.infrastructure.qualification_reader import QualificationReader
from src.modules.metrics.infrastructure.reader import MetricsLeadReader


class ReportUseCase:
    def __init__(self, reader: MetricsLeadReader, qualification: QualificationReader) -> None:
        self._reader = reader
        self._qualification = qualification

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict[str, object]:
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._qualification.build(store_ids)
        return build_report_processed(leads, start, end, ctx.passed)
