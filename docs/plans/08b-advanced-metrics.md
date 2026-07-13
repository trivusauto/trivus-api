# Plano 08b — Métricas avançadas (qualificação, séries, modo indicadores, global admin)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 05, 08 e 09. Fecha as lacunas encontradas espelhando o front. Código copia-e-cola.

**Goal:** Completar as métricas para bater 100% com o front: (1) contagem de **qualificados** via contexto de alcance de etapa (spec §6.5); (2) **séries mensais** (dashboard 12m); (3) **modo indicadores** (dashboard/relatórios a partir de `daily_indicators`) + `goalsComparison`; (4) **métricas globais do admin** (todas as lojas).

**Architecture:** Estende o módulo `metrics`. Novas funções puras em `domain`, um `StageReachReader` **genérico** na infra (parametrizado pela etapa: QUALIFICADOS aqui; o Plano 10b reusa para CLASSIFICADOS), e wiring nos use cases/router.

> **Revisão (spec de marketing, 02/07/2026):** a tela de Marketing antiga foi considerada redundante e **será reconstruída do zero no Plano 10b** — por isso este plano NÃO cria endpoint `/metrics/marketing`.

---

## Task 1: Contexto de alcance de etapa (o `qualified` sai de 0)

**Files:** `src/modules/metrics/domain/stage_reach.py`, `src/modules/metrics/infrastructure/stage_reach_reader.py` + testes

> Porta de `fetchCrmQualificationContext` / `leadPassedQualificadosStage` (spec §6.5): um lead "alcançou a etapa X" se **entrou** na coluna X (histórico) **ou** sua coluna atual é X ou posterior (no funil clonado do template). **Genérico por etapa**: usado aqui com QUALIFICADOS; o Plano 10b (marketing) reusa com CLASSIFICADOS.

- [ ] **Step 1: Teste do predicado (puro)**

`tests/unit/metrics/test_stage_reach.py`:
```python
from src.modules.metrics.domain.stage_reach import StageReachContext


def test_passed_by_history() -> None:
    ctx = StageReachContext(stage_ids_at_or_after={"st3"}, leads_with_history={"l1"})
    assert ctx.passed({"id": "l1", "stage_id": "st0"}) is True


def test_passed_by_current_stage() -> None:
    ctx = StageReachContext(stage_ids_at_or_after={"st3", "st4"}, leads_with_history=set())
    assert ctx.passed({"id": "l2", "stage_id": "st4"}) is True
    assert ctx.passed({"id": "l3", "stage_id": "st0"}) is False
```

- [ ] **Step 2: Rodar e ver falhar → implementar o contexto**

`src/modules/metrics/domain/stage_reach.py`:
```python
class StageReachContext:
    """Lead 'alcançou a etapa X': entrou nela (histórico) ou está nela/posterior."""

    def __init__(self, stage_ids_at_or_after: set[str], leads_with_history: set[str]) -> None:
        self._at_or_after = stage_ids_at_or_after
        self._leads_with_history = leads_with_history

    def passed(self, lead: dict) -> bool:
        if lead.get("id") in self._leads_with_history:
            return True
        return bool(lead.get("stage_id") and str(lead["stage_id"]) in self._at_or_after)
```
```bash
uv run pytest tests/unit/metrics/test_stage_reach.py
```
Expected: PASSA.

- [ ] **Step 3: Reader (constrói o contexto a partir do banco, parametrizado pela etapa)**

`src/modules/metrics/infrastructure/stage_reach_reader.py`:
```python
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.domain.stage_rules import StageRules
from src.modules.crm.infrastructure.orm import FunnelModel, StageHistoryModel, StageModel
from src.modules.metrics.domain.stage_reach import StageReachContext


class StageReachReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._rules = StageRules()

    async def build(self, store_ids: list[str], stage_name: str) -> StageReachContext:
        target = self._rules.normalize_stage_name(stage_name)
        if not store_ids:
            return StageReachContext(set(), set())
        funnel_ids = list((await self._session.execute(
            select(FunnelModel.id).where(FunnelModel.store_id.in_(store_ids), FunnelModel.template_source_id.isnot(None))
        )).scalars().all())
        if not funnel_ids:
            return StageReachContext(set(), set())

        stages = list((await self._session.execute(
            select(StageModel).where(StageModel.funnel_id.in_(funnel_ids)).order_by(StageModel.sort_order)
        )).scalars().all())

        by_funnel: dict[str, list] = defaultdict(list)
        for s in stages:
            by_funnel[s.funnel_id].append(s)

        target_ids: set[str] = set()
        at_or_after: set[str] = set()
        for fstages in by_funnel.values():
            fstages.sort(key=lambda s: s.sort_order or 0)
            ti = next((i for i, s in enumerate(fstages) if self._rules.normalize_stage_name(s.name) == target), -1)
            if ti < 0:
                continue
            target_ids.add(str(fstages[ti].id))
            for s in fstages[ti:]:
                at_or_after.add(str(s.id))

        leads_with_history: set[str] = set()
        if target_ids:
            rows = (await self._session.execute(
                select(StageHistoryModel.lead_id).where(StageHistoryModel.stage_id.in_(target_ids))
            )).scalars().all()
            leads_with_history = {str(r) for r in rows}

        return StageReachContext(at_or_after, leads_with_history)
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat(metrics): add generic stage reach context reader"
```

---

## Task 2: Wire qualificação + séries mensais

**Files:** Modify `src/modules/metrics/domain/metrics_core.py` (séries), `application/{dashboard.py,reports.py,marketing.py}`, `interface/{deps.py,router.py}`

- [ ] **Step 1: Funções de série (porta de `buildCrmMonthlySeriesForDashboard` / `buildCrmMarketingChartData`)**

Adicione ao fim de `src/modules/metrics/domain/metrics_core.py`:
```python
def _month_key(ymd: str | None) -> str | None:
    if not ymd:
        return None
    return f"{int(ymd[5:7])}/{int(ymd[0:4])}"


def build_monthly_series(leads: list[dict], month_keys: list[str], passed_qualificados=None) -> dict:
    acc = {k: {"leads": 0, "qualified": 0, "scheduled": 0, "attended": 0, "conversions": 0, "profitability": 0.0} for k in month_keys}
    for lead in leads:
        mk = _month_key(to_local_ymd(lead.get("created_at")))
        if mk in acc:
            acc[mk]["leads"] += 1
            if passed_qualificados and passed_qualificados(lead):
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
                    acc[mkf]["profitability"] += float(r)
    return acc


def last_month_keys(now, count: int) -> list[str]:
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
```

- [ ] **Step 2: Atualizar `DashboardUseCase` (qualificação + série 12m)**

Substitua `src/modules/metrics/application/dashboard.py` por:
```python
from datetime import date
from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range, build_monthly_series, last_month_keys


class DashboardUseCase:
    def __init__(self, reader, stage_reach) -> None:
        self._reader = reader
        self._stage_reach = stage_reach

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict:
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        totals = aggregate_totals_for_range(leads, start, end, ctx.passed)
        keys = last_month_keys(date.today(), 12)
        series = build_monthly_series(leads, keys, ctx.passed)
        return {"totals": totals, "monthly": [{"month": k, **series[k]} for k in keys]}
```

- [ ] **Step 3: Atualizar `ReportUseCase` (qualificação)**

Substitua `src/modules/metrics/application/reports.py` por:
```python
from src.modules.metrics.domain.metrics_core import build_report_processed


class ReportUseCase:
    def __init__(self, reader, stage_reach) -> None:
        self._reader = reader
        self._stage_reach = stage_reach

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict:
        leads = await self._reader.leads_for_stores(store_ids)
        ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        return build_report_processed(leads, start, end, ctx.passed)
```

- [ ] **Step 4: ~~MarketingUseCase~~ (REMOVIDO)**

> **Revisão da spec de marketing (02/07/2026):** a tela de Marketing antiga era redundante com o relatório e será **reconstruída do zero no Plano 10b** (funil de custos, campanhas, ROAS/ROI). Não crie `marketing.py` nem rota `/metrics/marketing` aqui. Nada a fazer neste step.

- [ ] **Step 5: Atualizar deps (injetar o stage reach)**

Em `src/modules/metrics/interface/deps.py`, adicione o import e ajuste os providers:
```python
from src.modules.metrics.infrastructure.stage_reach_reader import StageReachReader
# substitua os providers de dashboard/report:
def get_dashboard_uc(session: AsyncSession = Depends(get_session)) -> DashboardUseCase:
    return DashboardUseCase(MetricsLeadReader(session), StageReachReader(session))
def get_report_uc(session: AsyncSession = Depends(get_session)) -> ReportUseCase:
    return ReportUseCase(MetricsLeadReader(session), StageReachReader(session))
```
Nenhuma rota nova no router aqui (o `dashboard` agora retorna `{totals, monthly}`).

- [ ] **Step 6: Ajustar testes existentes + commit**

O teste e2e do Plano 08 esperava `total_leads` no topo do dashboard; agora vem em `body["totals"]["total_leads"]`. Ajuste `tests/e2e/test_metrics.py`. Rode tudo.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): wire qualification and monthly series"
```

---

## Task 3: Modo indicadores (dashboard/relatórios a partir de `daily_indicators`)

**Files:** `src/modules/metrics/domain/indicators_report.py` + teste, `application/indicators_report.py`, rota.

> Porta fiel de `processReportData` (`app/reports/page.js`, modo indicadores). Regra: `total`/`qualified` **só receptivo**; `revenue` = `profitability − daily_expenses` (net).

- [ ] **Step 1: Teste**

`tests/unit/metrics/test_indicators_report.py`:
```python
from src.modules.metrics.domain.indicators_report import build_indicators_report


def ind(**o):
    base = {"origin": "receptivo", "total_leads": 0, "qualified_leads": 0, "scheduled_leads": 0,
            "attended_leads": 0, "converted_leads": 0, "profitability": 0, "daily_expenses": 0}
    base.update(o)
    return base


def test_net_revenue_and_receptivo_only_total() -> None:
    indicators = [ind(origin="receptivo", total_leads=10, qualified_leads=6, converted_leads=2, profitability=1000, daily_expenses=200),
                  ind(origin="prospeccao", total_leads=99, converted_leads=1, profitability=500, daily_expenses=100)]
    res = build_indicators_report(indicators, [])
    assert res["summary"]["totalLeads"] == 10        # só receptivo
    assert res["summary"]["qualified"] == 6
    assert res["summary"]["converted"] == 3          # soma todos
    assert res["summary"]["revenue"] == 800 + 400    # net por origem


def test_goals_comparison() -> None:
    indicators = [ind(origin="receptivo", converted_leads=2, profitability=1000, daily_expenses=0)]
    goals = [{"origin": "receptivo", "conversions_quantity": 5, "profitability_goal": 3000}]
    res = build_indicators_report(indicators, goals)
    gc = res["goalsComparison"][0]
    assert gc["origin"] == "Receptivo"
    assert gc["Meta Conversões"] == 5 and gc["Real Conversões"] == 2
    assert gc["Meta Receita"] == 3000 and gc["Real Receita"] == 1000
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/metrics/domain/indicators_report.py`:
```python
def net_profitability(ind: dict) -> float:
    return float(ind.get("profitability") or 0) - float(ind.get("daily_expenses") or 0)


_LABEL = {"receptivo": "Receptivo", "prospeccao": "Prospecção", "outros": "Outros"}


def build_indicators_report(indicators: list[dict], goals: list[dict]) -> dict:
    def empty() -> dict:
        return {"total": 0, "qualified": 0, "scheduled": 0, "attended": 0, "converted": 0, "revenue": 0.0}
    by = {"receptivo": empty(), "prospeccao": empty(), "outros": empty()}
    for ind in indicators:
        o = ind.get("origin")
        if o not in by:
            continue
        if o == "receptivo":
            by[o]["total"] += ind.get("total_leads") or 0
            by[o]["qualified"] += ind.get("qualified_leads") or 0
        by[o]["scheduled"] += ind.get("scheduled_leads") or 0
        by[o]["attended"] += ind.get("attended_leads") or 0
        by[o]["converted"] += ind.get("converted_leads") or 0
        by[o]["revenue"] += net_profitability(ind)

    goals_comparison = []
    for goal in goals:
        origin_inds = [i for i in indicators if i.get("origin") == goal.get("origin")]
        conversions = sum(i.get("converted_leads") or 0 for i in origin_inds)
        revenue = sum(net_profitability(i) for i in origin_inds)
        goals_comparison.append({
            "origin": _LABEL.get(goal.get("origin"), "Outros"),
            "Meta Conversões": goal.get("conversions_quantity") or 0,
            "Real Conversões": conversions,
            "Meta Receita": float(goal.get("profitability_goal") or 0),
            "Real Receita": revenue,
        })

    total_converted = by["receptivo"]["converted"] + by["prospeccao"]["converted"] + by["outros"]["converted"]
    total_revenue = by["receptivo"]["revenue"] + by["prospeccao"]["revenue"] + by["outros"]["revenue"]
    return {
        "summary": {
            "totalLeads": by["receptivo"]["total"],
            "qualified": by["receptivo"]["qualified"],
            "scheduled": sum(by[o]["scheduled"] for o in by),
            "attended": sum(by[o]["attended"] for o in by),
            "converted": total_converted,
            "revenue": total_revenue,
            "avgTicket": (total_revenue / total_converted) if total_converted > 0 else 0.0,
        },
        "byOrigin": by,
        "goalsComparison": goals_comparison,
    }
```
```bash
uv run pytest tests/unit/metrics/test_indicators_report.py
```
Expected: PASSA.

- [ ] **Step 3: Use case + rota + commit**

`src/modules/metrics/application/indicators_report.py`:
```python
from src.modules.metrics.domain.indicators_report import build_indicators_report


class IndicatorsReportUseCase:
    def __init__(self, indicators_repo, goals_repo) -> None:
        self._indicators = indicators_repo
        self._goals = goals_repo

    async def execute(self, store_id: str, date_from: str, date_to: str, year: int, month: int) -> dict:
        indicators = await self._indicators.list(store_id, date_from, date_to)
        goals = await self._goals.list(store_id, year, month)
        return build_indicators_report(indicators, goals)
```
Adicione rota `GET /metrics/indicators-report?store_id=&from=&to=&year=&month=` (usa `IndicatorRepository` do Plano 09 e o repositório de `goals`). Provider no `deps.py`.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): add indicators-mode report"
```

---

## Task 4: Métricas globais do admin (todas as lojas)

**Files:** Modify `src/modules/metrics/interface/router.py` (`_resolve`), `deps.py`

> Hoje `_resolve` levanta erro se admin não passar `store_id`. O admin deve agregar **todas** as lojas.

- [ ] **Step 1: Ajustar `_resolve` para listar todas as lojas do admin**

Em `src/modules/metrics/interface/deps.py`, adicione um provider de todas as lojas:
```python
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreRepository


def get_store_repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemyStoreRepository:
    return SqlAlchemyStoreRepository(session)
```
Em `src/modules/metrics/interface/router.py`, substitua `_resolve` por uma versão que recebe o repositório de lojas:
```python
async def _resolve(user, store_id, access, stores) -> list[str]:
    scope = await access.execute(user)
    if store_id:
        if scope is not None and store_id not in scope:
            raise DomainError("Loja fora do escopo.")
        return [store_id]
    if scope is None:  # admin → todas as lojas
        return [s.id for s in await stores.list_all()]
    return scope
```
E injete `stores: SqlAlchemyStoreRepository = Depends(get_store_repo)` em cada rota, passando-o ao `_resolve`.

- [ ] **Step 2: Rodar + commit + concluir**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): admin global metrics across all stores"
```
Adicione uma linha do Plano 08b em [`00-INDEX.md`](./00-INDEX.md) (roadmap) marcando ✅ ao concluir.

---

## Resultado

- `qualified` correto (contexto de qualificação), séries mensais (dashboard 12m + marketing 6m), modo indicadores com `goalsComparison`, e métricas globais do admin. Cobertura de métricas agora bate com o front.

**Próximo:** [`05b-crm-templates.md`](./05b-crm-templates.md).
