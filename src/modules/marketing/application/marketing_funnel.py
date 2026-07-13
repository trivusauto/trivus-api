from typing import cast

from src.modules.marketing.domain.cost_funnel import build_cost_funnel
from src.modules.metrics.domain.metrics_core import (
    aggregate_totals_for_range, normalize_funil_key, to_local_ymd, traffic_light, ymd_in_range,
)

_GOAL_FIELD = {"leads": "leads_quantity", "qualified": "qualified_quantity",
               "scheduled": "scheduled_quantity", "attended": "attended_quantity",
               "sales": "conversions_quantity"}


class MarketingFunnelUseCase:
    """Funil receptivo com custos (Seção 1 da tela nova). Prospecção ativa fica de fora.
    Com campaign_id: filtra os leads da campanha e usa o budget como investimento (D3)."""

    def __init__(self, reader, stage_reach, investment, campaigns, goals) -> None:  # type: ignore[no-untyped-def]
        self._reader = reader
        self._stage_reach = stage_reach
        self._investment = investment
        self._campaigns = campaigns
        self._goals = goals

    async def execute(self, store_ids: list[str], start: str, end: str,
                      campaign_id: str | None = None) -> dict[str, object]:
        leads = await self._reader.leads_for_stores(store_ids)
        receptive = [lead for lead in leads if normalize_funil_key(lead.get("funil")) == "receptivo"]
        if campaign_id:
            receptive = [lead for lead in receptive if str(lead.get("campaign_id") or "") == campaign_id]

        c_ctx = await self._stage_reach.build(store_ids, "CLASSIFICADOS")
        q_ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        totals = aggregate_totals_for_range(receptive, start, end, q_ctx.passed)
        classified = sum(1 for lead in receptive
                         if ymd_in_range(to_local_ymd(lead.get("created_at")), start, end) and c_ctx.passed(lead))
        quantities = {"leads": int(totals["total_leads"]), "classified": classified,
                      "qualified": int(totals["qualified_leads"]), "scheduled": int(totals["scheduled"]),
                      "attended": int(totals["attended"]), "sales": int(totals["conversions"])}

        if campaign_id:
            camp = await self._campaigns.get(campaign_id)
            investment = float(camp.budget or 0) if camp else 0.0     # D3: budget da campanha
        else:
            investment = await self._investment.total(store_ids, start, end)   # D2: lançamentos diários

        funnel = build_cost_funnel(quantities, investment, float(totals["total_revenue"]))
        await self._apply_lights(funnel, store_ids, start, end, campaign_id)
        return funnel

    async def _apply_lights(self, funnel: dict[str, object], store_ids: list[str],
                            start: str, end: str, campaign_id: str | None) -> None:
        stages = cast(list[dict[str, object]], funnel["stages"])
        same_month = start[:7] == end[:7]
        if campaign_id or len(store_ids) != 1 or not same_month:    # D6: metas são mensais por loja
            for st in stages:
                st["goal"] = None
                st["pct_of_goal"] = None
                st["light"] = "gray"
            funnel["investment_goal"] = None
            return
        goals = await self._goals.list(store_ids[0], int(start[:4]), int(start[5:7]))
        receptivo_goal: dict[str, object] = next(
            (g for g in goals if g.get("origin") == "receptivo"), None) or {}
        for st in stages:
            field = _GOAL_FIELD.get(str(st["stage"]))
            goal = float(receptivo_goal.get(field) or 0) if field else 0.0  # type: ignore[arg-type]
            qty = float(cast(int, st["quantity"]))
            st["goal"] = goal or None
            st["pct_of_goal"] = (qty / goal * 100) if goal > 0 else None
            st["light"] = traffic_light(qty, goal)
        inv_goal = float(receptivo_goal.get("marketing_investment_goal") or 0)  # type: ignore[arg-type]
        funnel["investment_goal"] = inv_goal or None
