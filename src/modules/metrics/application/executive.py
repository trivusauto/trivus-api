"""Painel Executivo (spec PARTE C): KPIs do mês + recorte por unidade.

Dia útil aqui é **segunda a sábado** (as lojas abrem sábado) — regra própria da
planilha do cliente, diferente do `WorkingDays` das projeções, que também desconta
feriados. Todas as divisões são protegidas: loja sem venda devolve `None`, nunca 500.
"""
from calendar import monthrange
from datetime import date

WORKING_WEEKDAYS = (0, 1, 2, 3, 4, 5)   # seg(0) … sáb(5); domingo fica de fora


def _safe_div(num: float, den: float) -> float | None:
    return (num / den) if den else None


def working_days(year: int, month: int) -> int:
    last = monthrange(year, month)[1]
    return sum(1 for d in range(1, last + 1) if date(year, month, d).weekday() in WORKING_WEEKDAYS)


def worked_days(year: int, month: int, today: date) -> int:
    """Úteis decorridos se for o mês corrente; o mês inteiro se já passou."""
    if (today.year, today.month) != (year, month):
        return working_days(year, month)
    return sum(1 for d in range(1, today.day + 1) if date(year, month, d).weekday() in WORKING_WEEKDAYS)


def goal_status(realizado: float, meta: float) -> str:
    """Semáforo oficial — espelho do helper do front (≥95 / 80–95 / <80)."""
    if meta <= 0:
        return "amber"
    pct = realizado / meta
    if pct >= 0.95:
        return "green"
    return "amber" if pct >= 0.80 else "red"


class ExecutiveUseCase:
    def __init__(self, reader, goals) -> None:  # type: ignore[no-untyped-def]
        self._reader = reader
        self._goals = goals

    async def execute(
        self, store_ids: list[str], year: int, month: int, store_names: dict[str, str],
        today: date | None = None,
    ) -> dict[str, object]:
        today = today or date.today()
        last = monthrange(year, month)[1]
        start, end = f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"

        uteis = working_days(year, month)
        trabalhados = worked_days(year, month, today)
        restantes = max(uteis - trabalhados, 0)

        closings = await self._reader.closings_by_store(store_ids, start, end)
        leads = await self._reader.leads_by_store(store_ids, start, end)
        metas = await self._goals_by_store(store_ids, year, month)

        totals = {"faturamento": 0.0, "rentabilidade": 0.0, "meta": 0.0, "fechamentos": 0.0, "leads": 0.0}
        by_store: list[dict[str, object]] = []
        for sid in store_ids:
            c = closings.get(sid, {})
            faturamento = float(c.get("receita", 0.0))
            rentabilidade = float(c.get("rentabilidade", 0.0))
            fechamentos = int(c.get("fechamentos", 0))
            meta = metas.get(sid, 0.0)

            totals["faturamento"] += faturamento
            totals["rentabilidade"] += rentabilidade
            totals["meta"] += meta
            totals["fechamentos"] += fechamentos
            totals["leads"] += leads.get(sid, 0)

            margem = _safe_div(rentabilidade, faturamento)
            projecao = (faturamento / trabalhados * uteis) if trabalhados else 0.0
            by_store.append({
                "store_id": sid,
                "nome": store_names.get(sid, ""),
                "faturamento": faturamento,
                "meta": meta or None,
                "pct_meta": _safe_div(faturamento, meta),
                "ticket_medio": _safe_div(faturamento, fechamentos),
                "projecao": round(projecao, 2),
                "lucro_projetado": round(projecao * margem, 2) if margem is not None else None,
                "margem": margem,
                "fechamentos": fechamentos,
                "leads": leads.get(sid, 0),
                "status": goal_status(faturamento, meta),
            })

        return {
            "dias": {"uteis": uteis, "trabalhados": trabalhados, "restantes": restantes},
            "kpis": self._kpis(totals, uteis, trabalhados),
            "by_store": by_store,
        }

    async def _goals_by_store(self, store_ids: list[str], year: int, month: int) -> dict[str, float]:
        """Meta de faturamento da loja = Σ profitability_goal das origens."""
        out: dict[str, float] = {}
        for sid in store_ids:
            rows = await self._goals.list(sid, year, month)
            out[sid] = sum(float(g.get("profitability_goal") or 0) for g in rows)
        return out

    def _kpis(
        self, totals: dict[str, float], uteis: int, trabalhados: int
    ) -> dict[str, object]:
        faturamento = totals["faturamento"]
        meta = totals["meta"]
        fechamentos = int(totals["fechamentos"])
        leads = int(totals["leads"])

        margem_media = _safe_div(totals["rentabilidade"], faturamento)
        projecao = (faturamento / trabalhados * uteis) if trabalhados else 0.0
        return {
            "faturamento": faturamento,
            "meta": meta or None,
            "pct_meta": _safe_div(faturamento, meta),
            "projecao": round(projecao, 2),
            "pct_projecao": _safe_div(projecao, meta),
            "lucro_projetado": round(projecao * margem_media, 2) if margem_media is not None else None,
            "margem_media": margem_media,
            "ticket_medio": _safe_div(faturamento, fechamentos),
            "fechamentos": fechamentos,
            "conversao": _safe_div(fechamentos, leads),
        }
