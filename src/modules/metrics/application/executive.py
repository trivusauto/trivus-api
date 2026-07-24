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

        kpis = self._kpis(totals, uteis, trabalhados)
        vehicles = await self._reader.vehicle_counts_by_store(store_ids, start, end)
        return {
            "dias": {"uteis": uteis, "trabalhados": trabalhados, "restantes": restantes},
            "kpis": kpis,
            "by_store": by_store,
            "charts": self._charts(by_store, vehicles),
            "gauge": {"pct_meta": kpis["pct_meta"]},
            "ritmo": self._ritmo(kpis, trabalhados, restantes),
            "tops": self._tops(by_store),
            "resumo": self._resumo(kpis, by_store, restantes),
        }

    def _charts(
        self, by_store: list[dict[str, object]], vehicles: dict[str, dict[str, int]]
    ) -> dict[str, object]:
        """Séries prontas para os 6 gráficos da spec C4 — o front só plota."""
        def row(s: dict[str, object]) -> str:
            return str(s["nome"])

        faturamento_meta = [
            {"nome": row(s), "faturamento": s["faturamento"], "meta": s["meta"] or 0,
             "projecao": s["projecao"]}
            for s in by_store
        ]
        ranking = sorted(
            [{"nome": row(s), "faturamento": s["faturamento"]} for s in by_store],
            key=lambda r: float(r["faturamento"]), reverse=True,  # type: ignore[arg-type]
        )
        ticket_medio = sorted(
            [{"nome": row(s), "ticket_medio": s["ticket_medio"] or 0} for s in by_store],
            key=lambda r: float(r["ticket_medio"]), reverse=True,  # type: ignore[arg-type]
        )
        comprados_vendidos = [
            {"nome": row(s),
             "comprados": vehicles.get(str(s["store_id"]), {}).get("comprados", 0),
             "vendidos": vehicles.get(str(s["store_id"]), {}).get("vendidos", 0)}
            for s in by_store
        ]
        lucro_projetado = [
            {"nome": row(s), "lucro_projetado": s["lucro_projetado"] or 0} for s in by_store
        ]
        margem = [
            {"nome": row(s), "margem": (float(s["margem"]) * 100) if s["margem"] is not None else 0}  # type: ignore[arg-type]
            for s in by_store
        ]
        return {
            "faturamento_meta": faturamento_meta,
            "ranking": ranking,
            "ticket_medio": ticket_medio,
            "comprados_vendidos": comprados_vendidos,
            "lucro_projetado": lucro_projetado,
            "margem": margem,
        }

    def _ritmo(self, kpis: dict[str, object], trabalhados: int, restantes: int) -> dict[str, object]:
        faturamento = float(kpis["faturamento"])  # type: ignore[arg-type]
        meta = float(kpis["meta"] or 0)  # type: ignore[arg-type]
        projecao = float(kpis["projecao"])  # type: ignore[arg-type]
        falta = max(meta - faturamento, 0.0)
        forecast = _safe_div(projecao, meta)
        return {
            "media_diaria_atual": _safe_div(faturamento, trabalhados),
            "media_diaria_necessaria": _safe_div(falta, restantes),
            # Forecast é teto 99%: nunca prometer certeza de bater a meta.
            "forecast_pct": min(99, round(forecast * 100)) if forecast is not None else None,
        }

    def _tops(self, by_store: list[dict[str, object]]) -> dict[str, object]:
        destaques = sorted(by_store, key=lambda s: float(s["faturamento"]), reverse=True)[:3]  # type: ignore[arg-type]
        com_margem = [s for s in by_store if s["margem"] is not None]
        atencao = sorted(com_margem, key=lambda s: float(s["margem"]))[:3]  # type: ignore[arg-type]
        return {
            "destaques": [
                {"nome": s["nome"], "faturamento": s["faturamento"], "margem": s["margem"]}
                for s in destaques
            ],
            "atencao": [
                {"nome": s["nome"], "margem": s["margem"], "pct_meta": s["pct_meta"]}
                for s in atencao
            ],
        }

    def _resumo(
        self, kpis: dict[str, object], by_store: list[dict[str, object]], restantes: int
    ) -> list[str]:
        """Bullets calculados (sem IA) — spec C5.3."""
        out: list[str] = []
        pct = kpis["pct_meta"]
        if pct is not None:
            out.append(f"{float(pct) * 100:.0f}% da meta atingida")  # type: ignore[arg-type]
        out.append(f"Projeção de fechamento: R$ {float(kpis['projecao']):,.0f}"  # type: ignore[arg-type]
                   .replace(",", "."))

        com_meta = [s for s in by_store if s["pct_meta"] is not None]
        if com_meta:
            melhor = max(com_meta, key=lambda s: float(s["pct_meta"]))  # type: ignore[arg-type]
            pior = min(com_meta, key=lambda s: float(s["pct_meta"]))  # type: ignore[arg-type]
            out.append(f"Unidade destaque: {melhor['nome']}")
            if pior["store_id"] != melhor["store_id"]:
                out.append(f"Unidade que exige atenção: {pior['nome']}")

        meta = float(kpis["meta"] or 0)  # type: ignore[arg-type]
        falta = max(meta - float(kpis["faturamento"]), 0.0)  # type: ignore[arg-type]
        if restantes > 0 and falta > 0:
            diario = falta / restantes
            out.append(f"Necessário faturar ~R$ {diario:,.0f}/dia para atingir a meta".replace(",", "."))
        return out

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
