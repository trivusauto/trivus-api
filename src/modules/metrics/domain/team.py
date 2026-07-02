from typing import TypedDict
from src.modules.metrics.domain.metrics_core import date_col_to_ymd, to_local_ymd, ymd_in_range

_UNASSIGNED = "__unassigned__"


class _Row(TypedDict):
    user_id: str
    name: str
    shop_role: object
    leads: int
    scheduled: int
    attended: int
    converted: int
    revenue: float


def _has_appt(lead: dict[str, object]) -> bool:
    return bool(lead.get("data_agendamento") and lead.get("hora_agendamento"))


def _sched_ymd(lead: dict[str, object]) -> str | None:
    if not _has_appt(lead):
        return None
    return date_col_to_ymd(lead.get("data_marcacao_agendamento")) or date_col_to_ymd(lead.get("data_agendamento"))


def build_team_performance(
    leads: list[dict[str, object]], team_users: list[dict[str, object]], start: str, end: str
) -> dict[str, object]:
    stats: dict[str, _Row] = {}
    for u in team_users:
        uid = str(u["id"])
        stats[uid] = _Row(
            user_id=uid, name=str(u.get("name") or "—"), shop_role=u.get("shop_role"),
            leads=0, scheduled=0, attended=0, converted=0, revenue=0.0,
        )
    stats[_UNASSIGNED] = _Row(
        user_id=_UNASSIGNED, name="Sem responsável", shop_role=None,
        leads=0, scheduled=0, attended=0, converted=0, revenue=0.0,
    )

    def bump(uid: object, field: str, amount: float = 1.0) -> None:
        key = str(uid) if uid and str(uid) in stats else _UNASSIGNED
        row = stats[key]
        if field == "revenue":
            row["revenue"] += amount
        else:
            row[field] = row[field] + int(amount)  # type: ignore[literal-required]

    for lead in leads:
        if ymd_in_range(to_local_ymd(lead.get("created_at")), start, end):
            bump(lead.get("assigned_to"), "leads")
        if _has_appt(lead) and ymd_in_range(_sched_ymd(lead), start, end):
            bump(lead.get("vendedor_id") or lead.get("agendado_por"), "scheduled")
        if lead.get("compareceu_agendamento") is True and ymd_in_range(date_col_to_ymd(lead.get("data_compareceu")), start, end):
            bump(lead.get("vendedor_id"), "attended")
        if lead.get("fechou_negocio") is True and ymd_in_range(date_col_to_ymd(lead.get("data_fechou_negocio")), start, end):
            bump(lead.get("vendedor_id"), "converted")
            r = lead.get("rentabilidade")
            if r is not None:
                bump(lead.get("vendedor_id"), "revenue", float(r))  # type: ignore[arg-type]

    rows: list[dict[str, object]] = []
    for row in stats.values():
        if row["user_id"] == _UNASSIGNED and (row["leads"] + row["scheduled"] + row["attended"] + row["converted"] + row["revenue"]) == 0:
            continue
        conv_rate = (
            (row["converted"] / row["attended"] * 100) if row["attended"] > 0
            else ((row["converted"] / row["scheduled"] * 100) if row["scheduled"] > 0 else 0.0)
        )
        avg_ticket = (row["revenue"] / row["converted"]) if row["converted"] > 0 else 0.0
        rows.append({**row, "conversion_rate": conv_rate, "avg_ticket": avg_ticket})
    rows.sort(key=lambda x: (-float(x["revenue"]), -int(x["converted"]), str(x["name"])))  # type: ignore[call-overload, arg-type]
    return {"rows": rows}
