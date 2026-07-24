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
        return self._block(leads, start, end, ctx.passed, classified_ctx.passed)

    async def execute_multi(
        self, store_ids: list[str], start: str, end: str, store_names: dict[str, str]
    ) -> dict[str, object]:
        """Consolidado + recorte por loja, para o dono comparar unidades (S4.2).

        Uma única leitura de leads alimenta os dois blocos — o agrupamento por loja
        acontece sobre o mesmo resultado, sem query extra por loja.
        """
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        classified_ctx = await self._stage_reach.build(store_ids, "CLASSIFICADOS")

        by_store_leads: dict[str, list[dict[str, object]]] = {sid: [] for sid in store_ids}
        for lead in leads:
            bucket = by_store_leads.get(str(lead.get("store_id")))
            if bucket is not None:
                bucket.append(lead)

        return {
            "consolidated": self._block(leads, start, end, ctx.passed, classified_ctx.passed),
            "by_store": [
                {
                    "store_id": sid,
                    "store_name": store_names.get(sid, ""),
                    **self._block(by_store_leads[sid], start, end, ctx.passed, classified_ctx.passed),
                }
                for sid in store_ids
            ],
        }

    def _block(
        self, leads: list[dict[str, object]], start: str, end: str,
        passed_qualificados: object, passed_classificados: object,
    ) -> dict[str, object]:
        totals = aggregate_totals_for_range(leads, start, end, passed_qualificados, passed_classificados)
        keys = last_month_keys(date.today(), 12)
        series = build_monthly_series(leads, keys, passed_qualificados)
        return {"totals": totals, "monthly": [{"month": k, **series[k]} for k in keys]}
