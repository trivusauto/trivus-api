from datetime import date, datetime
from typing import TypedDict


def to_local_ymd(iso: object) -> str | None:
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.strftime("%Y-%m-%d")


def date_col_to_ymd(v: object) -> str | None:
    if v is None or v == "":
        return None
    s = str(v)
    return s[:10] if len(s) >= 10 else s


def ymd_in_range(ymd: str | None, start: str, end: str) -> bool:
    return bool(ymd and start <= ymd <= end)


def normalize_funil_key(funil: object) -> str:
    f = funil.strip() if isinstance(funil, str) else funil
    if not f or f == "receptivo":
        return "receptivo"
    if f == "prospeccao_ativa":
        return "prospeccao"
    return "outros"


def _has_appointment(lead: dict[str, object]) -> bool:
    return bool(lead.get("data_agendamento") and lead.get("hora_agendamento"))


def _schedule_marked_ymd(lead: dict[str, object]) -> str | None:
    if not _has_appointment(lead):
        return None
    return date_col_to_ymd(lead.get("data_marcacao_agendamento")) or date_col_to_ymd(lead.get("data_agendamento"))


class _Totals(TypedDict):
    total_leads: int
    qualified_leads: int
    scheduled: int
    attended: int
    conversions: int
    total_revenue: float


class _OriginStats(TypedDict):
    total: int
    qualified: int
    scheduled: int
    attended: int
    converted: int
    revenue: float


def aggregate_totals_for_range(
    leads: list[dict[str, object]], start: str, end: str, passed_qualificados: object = None
) -> dict[str, object]:
    t = _Totals(total_leads=0, qualified_leads=0, scheduled=0, attended=0, conversions=0, total_revenue=0.0)
    for lead in leads:
        if ymd_in_range(to_local_ymd(lead.get("created_at")), start, end):
            t["total_leads"] += 1
            if callable(passed_qualificados) and passed_qualificados(lead):
                t["qualified_leads"] += 1
        if _has_appointment(lead) and ymd_in_range(_schedule_marked_ymd(lead), start, end):
            t["scheduled"] += 1
        if lead.get("compareceu_agendamento") is True and ymd_in_range(date_col_to_ymd(lead.get("data_compareceu")), start, end):
            t["attended"] += 1
        if lead.get("fechou_negocio") is True and ymd_in_range(date_col_to_ymd(lead.get("data_fechou_negocio")), start, end):
            t["conversions"] += 1
            r = lead.get("rentabilidade")
            if r is not None:
                t["total_revenue"] += float(r)  # type: ignore[arg-type]
    return dict(t)


def aggregate_by_origin_for_range(
    leads: list[dict[str, object]], start: str, end: str, passed_qualificados: object = None
) -> dict[str, _OriginStats]:
    def empty() -> _OriginStats:
        return _OriginStats(total=0, qualified=0, scheduled=0, attended=0, converted=0, revenue=0.0)

    by: dict[str, _OriginStats] = {"receptivo": empty(), "prospeccao": empty(), "outros": empty()}
    for lead in leads:
        b = by[normalize_funil_key(lead.get("funil"))]
        if ymd_in_range(to_local_ymd(lead.get("created_at")), start, end):
            b["total"] += 1
            if callable(passed_qualificados) and passed_qualificados(lead):
                b["qualified"] += 1
        if _has_appointment(lead) and ymd_in_range(_schedule_marked_ymd(lead), start, end):
            b["scheduled"] += 1
        if lead.get("compareceu_agendamento") is True and ymd_in_range(date_col_to_ymd(lead.get("data_compareceu")), start, end):
            b["attended"] += 1
        if lead.get("fechou_negocio") is True and ymd_in_range(date_col_to_ymd(lead.get("data_fechou_negocio")), start, end):
            b["converted"] += 1
            r = lead.get("rentabilidade")
            if r is not None:
                b["revenue"] += float(r)  # type: ignore[arg-type]
    return by


def build_report_processed(
    leads: list[dict[str, object]], start: str, end: str, passed_qualificados: object = None
) -> dict[str, object]:
    by = aggregate_by_origin_for_range(leads, start, end, passed_qualificados)
    total_converted = sum(by[o]["converted"] for o in by)
    total_revenue = sum(by[o]["revenue"] for o in by)
    return {
        "summary": {
            "totalLeads": sum(by[o]["total"] for o in by),
            "qualified": sum(by[o]["qualified"] for o in by),
            "scheduled": sum(by[o]["scheduled"] for o in by),
            "attended": sum(by[o]["attended"] for o in by),
            "converted": total_converted,
            "revenue": total_revenue,
            "avgTicket": (total_revenue / total_converted) if total_converted > 0 else 0.0,
        },
        "byOrigin": by,
    }


def _month_key(ymd: str | None) -> str | None:
    if not ymd:
        return None
    return f"{int(ymd[5:7])}/{int(ymd[0:4])}"


class _MonthStats(TypedDict):
    leads: int
    qualified: int
    scheduled: int
    attended: int
    conversions: int
    profitability: float


def build_monthly_series(
    leads: list[dict[str, object]], month_keys: list[str], passed_qualificados: object = None
) -> dict[str, _MonthStats]:
    acc: dict[str, _MonthStats] = {
        k: _MonthStats(leads=0, qualified=0, scheduled=0, attended=0, conversions=0, profitability=0.0)
        for k in month_keys
    }
    for lead in leads:
        mk = _month_key(to_local_ymd(lead.get("created_at")))
        if mk in acc:
            acc[mk]["leads"] += 1
            if callable(passed_qualificados) and passed_qualificados(lead):
                acc[mk]["qualified"] += 1
        if _has_appointment(lead):
            mks = _month_key(_schedule_marked_ymd(lead))
            if mks in acc:
                acc[mks]["scheduled"] += 1
        if lead.get("compareceu_agendamento") is True:
            mkc = _month_key(date_col_to_ymd(lead.get("data_compareceu")))
            if mkc in acc:
                acc[mkc]["attended"] += 1
        if lead.get("fechou_negocio") is True:
            mkf = _month_key(date_col_to_ymd(lead.get("data_fechou_negocio")))
            if mkf in acc:
                acc[mkf]["conversions"] += 1
                r = lead.get("rentabilidade")
                if r is not None:
                    acc[mkf]["profitability"] += float(r)  # type: ignore[arg-type]
    return acc


def last_month_keys(now: date, count: int) -> list[str]:
    keys = []
    y, m = now.year, now.month
    for i in range(count - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        keys.append(f"{mm}/{yy}")
    return keys


def unit_cost(investment: float | None, qty: int) -> float | None:
    inv = float(investment or 0)
    return (inv / qty) if inv > 0 and qty > 0 else None


def traffic_light(value: float, goal: float | None) -> str:
    """Sinaleiro: verde >=100% da meta, amarelo >=80%, vermelho <80%, cinza sem meta (D4)."""
    g = float(goal or 0)
    if g <= 0:
        return "gray"
    pct = value / g * 100
    if pct >= 100:
        return "green"
    if pct >= 80:
        return "yellow"
    return "red"
