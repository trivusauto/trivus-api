from src.modules.metrics.domain.metrics_core import unit_cost

STAGE_ORDER = ["leads", "classified", "qualified", "scheduled", "attended", "sales"]
STAGE_LABELS = {"leads": "Leads", "classified": "Classificados", "qualified": "Qualificados",
                "scheduled": "Agendados", "attended": "Comparecidos", "sales": "Vendas"}


def build_cost_funnel(quantities: dict[str, int], investment: float | None, revenue: float) -> dict[str, object]:
    """Funil de marketing receptivo com custo por etapa (CPL…CAC), taxa de conversão
    da etapa anterior, ROAS e ROI (fórmulas da planilha da consultoria)."""
    inv = float(investment or 0)
    stages: list[dict[str, object]] = []
    prev_qty: int | None = None
    for key in STAGE_ORDER:
        qty = int(quantities.get(key) or 0)
        conversion = (qty / prev_qty * 100) if prev_qty else None
        stages.append({"stage": key, "label": STAGE_LABELS[key], "quantity": qty,
                       "unit_cost": unit_cost(inv, qty), "conversion_from_previous": conversion})
        prev_qty = qty
    roas = (revenue / inv) if inv > 0 else None
    roi = ((revenue - inv) / inv) if inv > 0 else None
    return {"stages": stages, "investment": inv, "revenue": revenue, "roas": roas, "roi": roi}
