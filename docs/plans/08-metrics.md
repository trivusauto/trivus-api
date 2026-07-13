# Plano 08 — Métricas (código completo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–05. Código copia-e-cola.

**Goal:** Read models a partir do CRM, preservando **exatamente** "qual data conta" (spec §6.5), performance por colaborador (§6.6) e projeções por dias úteis (§6.13) — corrigindo UTC e feriados móveis (§10.1).

**Architecture:** Módulo `metrics`. `metrics_core` e `working_days` são domínio puro. Reader reusa `lead_to_dict` do Plano 05. Escopo por loja via `GetAccessibleStoreIdsUseCase` (Plano 04).

> **Espelho do front:** `app/dashboard` usa `aggregateCrmTotalsForRange` (cards) + série mensal; `app/marketing` usa `aggregateCrmByOriginForRange`; `app/reports` usa `buildCrmReportProcessedData` → `{summary, byOrigin, goalsComparison}`; no modo indicadores, `totalLeads/qualified` contam **só receptivo**; `app/projections` usa totais + dias úteis. As chaves da API ficam em snake_case (o front novo adapta).
>
> Crie os `__init__.py` de `src/modules/metrics/` e subpastas, e de `tests/unit/metrics/`.

---

## Task 1: `metrics_core` (funções puras)

**Files:** `src/modules/metrics/domain/metrics_core.py` + `tests/unit/metrics/test_metrics_core.py`

- [ ] **Step 1: Teste**

`tests/unit/metrics/test_metrics_core.py`:
```python
from src.modules.metrics.domain.metrics_core import aggregate_by_origin_for_range, aggregate_totals_for_range, normalize_funil_key


def lead(**over):
    base = {"created_at": "2026-02-10T12:00:00Z", "funil": "receptivo", "stage_id": None,
            "data_agendamento": None, "hora_agendamento": None, "data_marcacao_agendamento": None,
            "compareceu_agendamento": False, "data_compareceu": None,
            "fechou_negocio": False, "data_fechou_negocio": None, "rentabilidade": None}
    base.update(over)
    return base


def test_normalize_funil() -> None:
    assert normalize_funil_key("prospeccao_ativa") == "prospeccao"
    assert normalize_funil_key("") == "receptivo"
    assert normalize_funil_key("xpto") == "outros"


def test_total_leads() -> None:
    assert aggregate_totals_for_range([lead()], "2026-02-01", "2026-02-28")["total_leads"] == 1


def test_scheduled_by_marcacao() -> None:
    t = aggregate_totals_for_range([lead(data_agendamento="2026-02-20", hora_agendamento="10:00", data_marcacao_agendamento="2026-02-05")], "2026-02-01", "2026-02-10")
    assert t["scheduled"] == 1


def test_conversions_and_revenue() -> None:
    t = aggregate_totals_for_range([lead(fechou_negocio=True, data_fechou_negocio="2026-02-12", rentabilidade=1500)], "2026-02-01", "2026-02-28")
    assert t["conversions"] == 1 and t["total_revenue"] == 1500


def test_by_origin() -> None:
    by = aggregate_by_origin_for_range([lead(funil="prospeccao_ativa")], "2026-02-01", "2026-02-28")
    assert by["prospeccao"]["total"] == 1 and by["receptivo"]["total"] == 0
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/metrics/domain/metrics_core.py`:
```python
from datetime import datetime


def to_local_ymd(iso: str | None) -> str | None:
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


def _has_appointment(lead: dict) -> bool:
    return bool(lead.get("data_agendamento") and lead.get("hora_agendamento"))


def _schedule_marked_ymd(lead: dict) -> str | None:
    if not _has_appointment(lead):
        return None
    return date_col_to_ymd(lead.get("data_marcacao_agendamento")) or date_col_to_ymd(lead.get("data_agendamento"))


def aggregate_totals_for_range(leads: list[dict], start: str, end: str, passed_qualificados=None) -> dict:
    t = {"total_leads": 0, "qualified_leads": 0, "scheduled": 0, "attended": 0, "conversions": 0, "total_revenue": 0.0}
    for lead in leads:
        if ymd_in_range(to_local_ymd(lead.get("created_at")), start, end):
            t["total_leads"] += 1
            if passed_qualificados and passed_qualificados(lead):
                t["qualified_leads"] += 1
        if _has_appointment(lead) and ymd_in_range(_schedule_marked_ymd(lead), start, end):
            t["scheduled"] += 1
        if lead.get("compareceu_agendamento") is True and ymd_in_range(date_col_to_ymd(lead.get("data_compareceu")), start, end):
            t["attended"] += 1
        if lead.get("fechou_negocio") is True and ymd_in_range(date_col_to_ymd(lead.get("data_fechou_negocio")), start, end):
            t["conversions"] += 1
            r = lead.get("rentabilidade")
            if r is not None:
                t["total_revenue"] += float(r)
    return t


def aggregate_by_origin_for_range(leads: list[dict], start: str, end: str, passed_qualificados=None) -> dict:
    def empty() -> dict:
        return {"total": 0, "qualified": 0, "scheduled": 0, "attended": 0, "converted": 0, "revenue": 0.0}
    by = {"receptivo": empty(), "prospeccao": empty(), "outros": empty()}
    for lead in leads:
        b = by[normalize_funil_key(lead.get("funil"))]
        if ymd_in_range(to_local_ymd(lead.get("created_at")), start, end):
            b["total"] += 1
            if passed_qualificados and passed_qualificados(lead):
                b["qualified"] += 1
        if _has_appointment(lead) and ymd_in_range(_schedule_marked_ymd(lead), start, end):
            b["scheduled"] += 1
        if lead.get("compareceu_agendamento") is True and ymd_in_range(date_col_to_ymd(lead.get("data_compareceu")), start, end):
            b["attended"] += 1
        if lead.get("fechou_negocio") is True and ymd_in_range(date_col_to_ymd(lead.get("data_fechou_negocio")), start, end):
            b["converted"] += 1
            r = lead.get("rentabilidade")
            if r is not None:
                b["revenue"] += float(r)
    return by


def build_report_processed(leads: list[dict], start: str, end: str, passed_qualificados=None) -> dict:
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
```
```bash
uv run pytest tests/unit/metrics/test_metrics_core.py
git add -A && git commit -m "feat(metrics): port metrics core"
```

---

## Task 2: `WorkingDays` (feriados móveis)

**Files:** `src/modules/metrics/domain/working_days.py` + `tests/unit/metrics/test_working_days.py`

- [ ] **Step 1: Teste**

`tests/unit/metrics/test_working_days.py`:
```python
from datetime import date
from src.modules.metrics.domain.working_days import WorkingDays

w = WorkingDays()


def test_sunday_excluded_saturday_counts() -> None:
    assert w.is_working_day(date(2026, 1, 4)) is False
    assert w.is_working_day(date(2026, 1, 3)) is True


def test_fixed_holiday() -> None:
    assert w.is_working_day(date(2026, 12, 25)) is False


def test_movable_holiday_good_friday_2026() -> None:
    assert w.is_working_day(date(2026, 4, 3)) is False


def test_working_days_in_month_positive() -> None:
    assert w.working_days_in_month(2026, 2) > 20
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/metrics/domain/working_days.py`:
```python
from calendar import monthrange
from datetime import date, timedelta


def _easter(year: int) -> date:
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month = (h + m - 7 * n + 114) // 31
    day = ((h + m - 7 * n + 114) % 31) + 1
    return date(year, month, day)


class WorkingDays:
    def _holidays(self, year: int) -> set[str]:
        easter = _easter(year)
        fixed = [f"{year}-01-01", f"{year}-04-21", f"{year}-05-01", f"{year}-09-07",
                 f"{year}-10-12", f"{year}-11-02", f"{year}-11-15", f"{year}-11-20", f"{year}-12-25"]
        movable = [(easter + timedelta(days=n)).isoformat() for n in (-48, -47, -2, 60)]
        return set(fixed) | set(movable)

    def is_holiday(self, d: date) -> bool:
        return d.isoformat() in self._holidays(d.year)

    def is_working_day(self, d: date) -> bool:
        return d.weekday() != 6 and not self.is_holiday(d)

    def count_working_days(self, start: date, end: date) -> int:
        count, cur = 0, start
        while cur <= end:
            if self.is_working_day(cur):
                count += 1
            cur += timedelta(days=1)
        return count

    def working_days_in_month(self, year: int, month: int) -> int:
        return self.count_working_days(date(year, month, 1), date(year, month, monthrange(year, month)[1]))

    def remaining_working_days(self, year: int, month: int, current_day: int) -> int:
        return self.count_working_days(date(year, month, current_day), date(year, month, monthrange(year, month)[1]))
```
```bash
uv run pytest tests/unit/metrics/test_working_days.py
git add -A && git commit -m "feat(metrics): add working days"
```

---

## Task 3: Reader + use cases + router

**Files:** `src/modules/metrics/infrastructure/reader.py`, `application/{dashboard.py,projections.py,reports.py}`, `interface/{deps.py,router.py}`, `src/main.py`

- [ ] **Step 1: Reader (reusa `lead_to_dict`)**

`src/modules/metrics/infrastructure/reader.py`:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.infrastructure.orm import LeadModel
from src.modules.crm.infrastructure.repositories import lead_to_dict


class MetricsLeadReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def leads_for_stores(self, store_ids: list[str]) -> list[dict]:
        if not store_ids:
            return []
        rows = (await self._session.execute(select(LeadModel).where(LeadModel.store_id.in_(store_ids)))).scalars().all()
        return [lead_to_dict(r) for r in rows]
```

- [ ] **Step 2: Use cases**

`src/modules/metrics/application/dashboard.py`:
```python
from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range


class DashboardUseCase:
    def __init__(self, reader) -> None:
        self._reader = reader

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict:
        return aggregate_totals_for_range(await self._reader.leads_for_stores(store_ids), start, end)
```
`src/modules/metrics/application/reports.py`:
```python
from src.modules.metrics.domain.metrics_core import build_report_processed


class ReportUseCase:
    def __init__(self, reader) -> None:
        self._reader = reader

    async def execute(self, store_ids: list[str], start: str, end: str) -> dict:
        return build_report_processed(await self._reader.leads_for_stores(store_ids), start, end)
```
`src/modules/metrics/application/projections.py`:
```python
from calendar import monthrange
from datetime import date
from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range
from src.modules.metrics.domain.working_days import WorkingDays


class ProjectionsUseCase:
    def __init__(self, reader, workdays: WorkingDays) -> None:
        self._reader = reader
        self._workdays = workdays

    async def execute(self, store_ids: list[str], year: int, month: int) -> dict:
        last = monthrange(year, month)[1]
        start, end = f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"
        totals = aggregate_totals_for_range(await self._reader.leads_for_stores(store_ids), start, end)
        today = date.today()
        current_day = today.day if (today.year, today.month) == (year, month) else last
        total_wd = self._workdays.working_days_in_month(year, month)
        remaining = self._workdays.remaining_working_days(year, month, current_day)
        elapsed = total_wd - remaining
        pace = totals["conversions"] / elapsed if elapsed > 0 else 0.0
        return {"totals": totals, "working_days": {"elapsed": elapsed, "remaining": remaining},
                "projected_conversions": round(totals["conversions"] + pace * remaining)}
```

- [ ] **Step 3: deps + router (escopo por loja)**

`src/modules/metrics/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.metrics.application.dashboard import DashboardUseCase
from src.modules.metrics.application.projections import ProjectionsUseCase
from src.modules.metrics.application.reports import ReportUseCase
from src.modules.metrics.domain.working_days import WorkingDays
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreAccessReader
from src.shared.infrastructure.database import get_session


def get_dashboard_uc(session: AsyncSession = Depends(get_session)) -> DashboardUseCase:
    return DashboardUseCase(MetricsLeadReader(session))


def get_report_uc(session: AsyncSession = Depends(get_session)) -> ReportUseCase:
    return ReportUseCase(MetricsLeadReader(session))


def get_projections_uc(session: AsyncSession = Depends(get_session)) -> ProjectionsUseCase:
    return ProjectionsUseCase(MetricsLeadReader(session), WorkingDays())


def get_accessible_uc(session: AsyncSession = Depends(get_session)) -> GetAccessibleStoreIdsUseCase:
    return GetAccessibleStoreIdsUseCase(SqlAlchemyStoreAccessReader(session))
```
`src/modules/metrics/interface/router.py`:
```python
from fastapi import APIRouter, Depends, Query
from src.modules.metrics.application.dashboard import DashboardUseCase
from src.modules.metrics.application.projections import ProjectionsUseCase
from src.modules.metrics.application.reports import ReportUseCase
from src.modules.metrics.interface.deps import get_accessible_uc, get_dashboard_uc, get_projections_uc, get_report_uc
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.shared.domain.errors import DomainError
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(prefix="/metrics", tags=["metrics"])


async def _resolve(user: CurrentUser, store_id: str | None, access: GetAccessibleStoreIdsUseCase) -> list[str]:
    scope = await access.execute(user)
    if store_id:
        if scope is not None and store_id not in scope:
            raise DomainError("Loja fora do escopo.")
        return [store_id]
    if scope is None:
        raise DomainError("Informe store_id.")
    return scope


@router.get("/dashboard")
async def dashboard(store_id: str | None = Query(None), start: str = Query(...), end: str = Query(...),
                    user: CurrentUser = Depends(get_current_user), uc: DashboardUseCase = Depends(get_dashboard_uc),
                    access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc)) -> dict:
    return await uc.execute(await _resolve(user, store_id, access), start, end)


@router.get("/reports")
async def reports(store_id: str | None = Query(None), start: str = Query(...), end: str = Query(...),
                  user: CurrentUser = Depends(get_current_user), uc: ReportUseCase = Depends(get_report_uc),
                  access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc)) -> dict:
    return await uc.execute(await _resolve(user, store_id, access), start, end)


@router.get("/projections")
async def projections(year: int = Query(...), month: int = Query(...), store_id: str | None = Query(None),
                      user: CurrentUser = Depends(get_current_user), uc: ProjectionsUseCase = Depends(get_projections_uc),
                      access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc)) -> dict:
    return await uc.execute(await _resolve(user, store_id, access), year, month)
```
Em `src/main.py`, inclua `from src.modules.metrics.interface.router import router as metrics_router` e `app.include_router(metrics_router)`.

> `DomainError` → HTTP 400 pelos handlers do Plano 03 Task 6.

- [ ] **Step 4: e2e + commit**

`tests/e2e/test_metrics.py`: login admin, cria loja, `GET /metrics/dashboard?store_id=..&start=2026-01-01&end=2026-12-31` → 200 com `total_leads == 0`.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): add dashboard, reports and projections endpoints"
```

---

## Task 4: Performance por colaborador (`team`)

**Files:** `src/modules/metrics/domain/team.py` + `tests/unit/metrics/test_team.py`, endpoint.

> Porta de `crmTeamMetrics.js` (spec §6.6). Atribuição: leads→`assigned_to`; agendamentos→`vendedor_id or agendado_por`; comparecimentos/conversões/receita→`vendedor_id`.

- [ ] **Step 1: Teste + função pura**

`tests/unit/metrics/test_team.py`:
```python
from src.modules.metrics.domain.team import build_team_performance


def lead(**o):
    base = {"created_at": "2026-02-10T12:00:00Z", "assigned_to": None, "vendedor_id": None, "agendado_por": None,
            "data_agendamento": None, "hora_agendamento": None, "data_marcacao_agendamento": None,
            "compareceu_agendamento": False, "data_compareceu": None,
            "fechou_negocio": False, "data_fechou_negocio": None, "rentabilidade": None}
    base.update(o)
    return base


def test_conversion_to_vendedor() -> None:
    res = build_team_performance(
        [lead(fechou_negocio=True, data_fechou_negocio="2026-02-12", rentabilidade=1000, vendedor_id="v1")],
        [{"id": "v1", "name": "Vend 1", "shop_role": "vendedor"}], "2026-02-01", "2026-02-28")
    row = next(r for r in res["rows"] if r["user_id"] == "v1")
    assert row["converted"] == 1 and row["revenue"] == 1000
```

- [ ] **Step 2: Implementar**

`src/modules/metrics/domain/team.py`:
```python
from src.modules.metrics.domain.metrics_core import date_col_to_ymd, to_local_ymd, ymd_in_range

_UNASSIGNED = "__unassigned__"


def _has_appt(lead: dict) -> bool:
    return bool(lead.get("data_agendamento") and lead.get("hora_agendamento"))


def _sched_ymd(lead: dict) -> str | None:
    if not _has_appt(lead):
        return None
    return date_col_to_ymd(lead.get("data_marcacao_agendamento")) or date_col_to_ymd(lead.get("data_agendamento"))


def build_team_performance(leads: list[dict], team_users: list[dict], start: str, end: str) -> dict:
    stats: dict[str, dict] = {}
    for u in team_users:
        stats[u["id"]] = {"user_id": u["id"], "name": u.get("name") or "—", "shop_role": u.get("shop_role"),
                          "leads": 0, "scheduled": 0, "attended": 0, "converted": 0, "revenue": 0.0}
    stats[_UNASSIGNED] = {"user_id": _UNASSIGNED, "name": "Sem responsável", "shop_role": None,
                          "leads": 0, "scheduled": 0, "attended": 0, "converted": 0, "revenue": 0.0}

    def bump(uid: str | None, field: str, amount: float = 1) -> None:
        key = uid if uid and uid in stats else _UNASSIGNED
        stats[key][field] += amount

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
                bump(lead.get("vendedor_id"), "revenue", float(r))

    rows = []
    for r in stats.values():
        if r["user_id"] == _UNASSIGNED and (r["leads"] + r["scheduled"] + r["attended"] + r["converted"] + r["revenue"]) == 0:
            continue
        conv_rate = (r["converted"] / r["attended"] * 100) if r["attended"] > 0 else ((r["converted"] / r["scheduled"] * 100) if r["scheduled"] > 0 else 0.0)
        avg_ticket = (r["revenue"] / r["converted"]) if r["converted"] > 0 else 0.0
        rows.append({**r, "conversion_rate": conv_rate, "avg_ticket": avg_ticket})
    rows.sort(key=lambda x: (-x["revenue"], -x["converted"], x["name"]))
    return {"rows": rows}
```
```bash
uv run pytest tests/unit/metrics/test_team.py
git add -A && git commit -m "feat(metrics): add team performance"
```

- [ ] **Step 3: Endpoint + concluir**

Adicione `GET /metrics/team?store_id=&start=&end=` no router: resolve escopo, busca a equipe (`SqlAlchemyUserRepository.list_team(store_id)` + dono via `get_by_id(store_id)` — o dono é o usuário `client` cujo id == store_id no legado; no modelo novo, use os vínculos `user_store_access` com `is_owner`), monta `team_users` (`[{"id","name","shop_role"}]`) e chama `build_team_performance(reader.leads_for_stores([store_id]), team_users, start, end)`.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): add team endpoint"
```
Atualize o status do Plano 08 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Resultado

- Dashboard, relatórios, projeções e equipe via API, com regras de contagem idênticas ao front e dias úteis corretos.

**Próximo:** [`09-legacy-goals-plans.md`](./09-legacy-goals-plans.md).
