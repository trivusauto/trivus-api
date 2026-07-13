from calendar import monthrange
from datetime import date
from typing import cast

from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range, traffic_light
from src.modules.metrics.domain.working_days import WorkingDays

_METRICS = [("leads", "total_leads", "leads_quantity"),
            ("qualified", "qualified_leads", "qualified_quantity"),
            ("scheduled", "scheduled", "scheduled_quantity"),
            ("attended", "attended", "attended_quantity"),
            ("conversions", "conversions", "conversions_quantity"),
            ("revenue", "total_revenue", "profitability_goal")]


class ProjectionsUseCase:
    """Trio Meta / Realizado / Projetando por indicador, com % da meta e sinaleiro.
    Projeção pelo ritmo dos dias úteis (sábado conta, domingo e feriados não)."""

    def __init__(self, reader, workdays: WorkingDays, stage_reach, goals) -> None:  # type: ignore[no-untyped-def]
        self._reader = reader
        self._workdays = workdays
        self._stage_reach = stage_reach
        self._goals = goals

    async def execute(self, store_ids: list[str], year: int, month: int) -> dict[str, object]:
        last = monthrange(year, month)[1]
        start, end = f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        totals = aggregate_totals_for_range(leads, start, end, ctx.passed)

        today = date.today()
        current_day = today.day if (today.year, today.month) == (year, month) else last
        total_wd = self._workdays.working_days_in_month(year, month)
        remaining = self._workdays.remaining_working_days(year, month, current_day)
        elapsed = max(total_wd - remaining, 0)

        goals_row: dict[str, float] = {}
        if len(store_ids) == 1:  # metas são mensais por loja (D6)
            for g in await self._goals.list(store_ids[0], year, month):
                for _, _, gf in _METRICS:
                    goals_row[gf] = goals_row.get(gf, 0.0) + float(g.get(gf) or 0)

        metrics: list[dict[str, object]] = []
        totals_map: dict[str, object] = dict(totals)
        for key, tf, gf in _METRICS:
            actual = float(cast(float, totals_map[tf]))
            pace = actual / elapsed if elapsed > 0 else 0.0
            projected = round(actual + pace * remaining, 2)
            goal = goals_row.get(gf, 0.0)
            metrics.append({"key": key, "goal": goal or None, "actual": actual, "projected": projected,
                            "pct_of_goal": (projected / goal * 100) if goal > 0 else None,
                            "light": traffic_light(projected, goal)})
        return {"working_days": {"total": total_wd, "elapsed": elapsed, "remaining": remaining},
                "metrics": metrics}
