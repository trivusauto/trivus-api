from src.modules.metrics.domain.metrics_core import build_report_processed
from src.modules.metrics.infrastructure.investment_reader import InvestmentReader
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.metrics.infrastructure.stage_reach_reader import StageReachReader


class ReportUseCase:
    def __init__(self, reader: MetricsLeadReader, stage_reach: StageReachReader,
                 investment: InvestmentReader) -> None:
        self._reader = reader
        self._stage_reach = stage_reach
        self._investment = investment

    async def execute(self, store_ids: list[str], start: str, end: str,
                      campaign_id: str | None = None) -> dict[str, object]:
        leads = await self._reader.leads_for_stores(store_ids)
        if campaign_id:
            leads = [lead for lead in leads if str(lead.get("campaign_id") or "") == campaign_id]
        q_ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        c_ctx = await self._stage_reach.build(store_ids, "CLASSIFICADOS")
        inv = await self._investment.total(store_ids, start, end)
        return build_report_processed(leads, start, end, q_ctx.passed, c_ctx.passed, inv)
