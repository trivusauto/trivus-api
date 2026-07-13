from src.modules.metrics.domain.metrics_core import build_report_processed
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.metrics.infrastructure.stage_reach_reader import StageReachReader


class ReportUseCase:
    def __init__(self, reader: MetricsLeadReader, stage_reach: StageReachReader) -> None:
        self._reader = reader
        self._stage_reach = stage_reach

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict[str, object]:
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        return build_report_processed(leads, start, end, ctx.passed)
