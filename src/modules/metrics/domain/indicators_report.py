from typing import TypedDict

from src.modules.metrics.domain.metrics_core import unit_cost


def _net(ind: dict[str, object]) -> float:
    return float(ind.get("profitability") or 0) - float(ind.get("daily_expenses") or 0)  # type: ignore[arg-type]


def _investment(ind: dict[str, object]) -> float:
    return float(ind.get("marketing_investment") or 0)  # type: ignore[arg-type]


_LABEL: dict[str, str] = {"receptivo": "Receptivo", "prospeccao": "Prospecção", "outros": "Outros"}


class _OriginBucket(TypedDict):
    total: int
    classified: int
    qualified: int
    scheduled: int
    attended: int
    converted: int
    revenue: float


def build_indicators_report(
    indicators: list[dict[str, object]], goals: list[dict[str, object]]
) -> dict[str, object]:
    """Relatório do modo indicadores. Regras do front preservadas:
    total/qualified/classified contam só receptivo; receita é líquida (bruto − despesas).
    Marketing: investimento acumulado, custos por etapa e meta de investimento."""
    def empty() -> _OriginBucket:
        return _OriginBucket(total=0, classified=0, qualified=0, scheduled=0,
                             attended=0, converted=0, revenue=0.0)

    by: dict[str, _OriginBucket] = {"receptivo": empty(), "prospeccao": empty(), "outros": empty()}
    investment = 0.0
    for ind in indicators:
        investment += _investment(ind)
        o = str(ind.get("origin") or "")
        if o not in by:
            continue
        if o == "receptivo":
            by[o]["total"] += int(ind.get("total_leads") or 0)  # type: ignore[call-overload]
            by[o]["classified"] += int(ind.get("classified_leads") or 0)  # type: ignore[call-overload]
            by[o]["qualified"] += int(ind.get("qualified_leads") or 0)  # type: ignore[call-overload]
        by[o]["scheduled"] += int(ind.get("scheduled_leads") or 0)  # type: ignore[call-overload]
        by[o]["attended"] += int(ind.get("attended_leads") or 0)  # type: ignore[call-overload]
        by[o]["converted"] += int(ind.get("converted_leads") or 0)  # type: ignore[call-overload]
        by[o]["revenue"] += _net(ind)

    goals_comparison: list[dict[str, object]] = []
    for goal in goals:
        origin = str(goal.get("origin") or "")
        origin_inds = [i for i in indicators if str(i.get("origin") or "") == origin]
        conversions = sum(int(i.get("converted_leads") or 0) for i in origin_inds)  # type: ignore[call-overload]
        revenue = sum(_net(i) for i in origin_inds)
        origin_investment = sum(_investment(i) for i in origin_inds)
        goals_comparison.append({
            "origin": _LABEL.get(origin, "Outros"),
            "Meta Conversões": int(goal.get("conversions_quantity") or 0),  # type: ignore[call-overload]
            "Real Conversões": conversions,
            "Meta Receita": float(goal.get("profitability_goal") or 0),  # type: ignore[arg-type]
            "Real Receita": revenue,
            "Meta Investimento": float(goal.get("marketing_investment_goal") or 0),  # type: ignore[arg-type]
            "Real Investimento": origin_investment,
        })

    total_converted = by["receptivo"]["converted"] + by["prospeccao"]["converted"] + by["outros"]["converted"]
    total_revenue = by["receptivo"]["revenue"] + by["prospeccao"]["revenue"] + by["outros"]["revenue"]
    r = by["receptivo"]  # custos só sobre o receptivo (prospecção não tem investimento de mídia)
    costs = {
        "cost_per_lead": unit_cost(investment, r["total"]),
        "cost_per_classified": unit_cost(investment, r["classified"]),
        "cost_per_qualified": unit_cost(investment, r["qualified"]),
        "cost_per_scheduled": unit_cost(investment, r["scheduled"]),
        "cost_per_attended": unit_cost(investment, r["attended"]),
        "cac": unit_cost(investment, r["converted"]),
    }
    return {
        "summary": {
            "totalLeads": r["total"],
            "classified": r["classified"],
            "qualified": r["qualified"],
            "scheduled": sum(by[o]["scheduled"] for o in by),
            "attended": sum(by[o]["attended"] for o in by),
            "converted": total_converted,
            "revenue": total_revenue,
            "avgTicket": (total_revenue / total_converted) if total_converted > 0 else 0.0,
        },
        "byOrigin": by,
        "costs": costs,
        "investment": investment,
        "goalsComparison": goals_comparison,
    }
