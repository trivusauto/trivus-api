# Plano 10b — Módulo Marketing (campanhas, funil de custos, ROAS/ROI)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 05, 05b, 06, 08, 08b e 09. **Execute após o Plano 10 e antes do 11.** Código copia-e-cola.
>
> **Spec de origem:** reunião de 02/07/2026 (`MUDANCAS_MARKETING_RELATORIOS.md`) — funil de marketing com custo por etapa (CPL…CAC), campanhas como entidade, investimento nas metas/indicadores, e reconstrução da tela de Marketing.

**Goal:** Backend completo do módulo de marketing: CRUD de **campanhas**, **funil de custos** do receptivo (CPL, custo por classificado/qualificado/agendado/comparecido, CAC, taxas de conversão por etapa, ROAS, ROI, sinaleiros), **filtro por campanha** nos relatórios, **investimento** nas metas e indicadores, **classificados** como métrica, projeções com trio Meta/Realizado/Projetando, bloqueio de avanço sem campanha (`require_campaign_on_lead`) e auto-match de campanha no webhook.

**Architecture:** Novo módulo hexagonal `marketing/` (campanhas + funil de custos) + extensões nos módulos `metrics`, `crm` e `webhook`. `build_cost_funnel` e `match_campaign_by_link` são domínio puro. A prospecção ativa **não entra** no funil de custos (sem investimento de mídia).

**Tech Stack:** o mesmo do Plano 03.

---

## Decisões assumidas (validar na revisão humana)

| # | Decisão | Justificativa |
|---|---------|---------------|
| D1 | **Auto-match de campanha** via `link_code` cadastrado na campanha, procurado no payload do webhook (campos de referral/anúncio e texto da mensagem). | A spec diz "identificar pelo link do WhatsApp" sem detalhar o payload. **Validar com um payload real de anúncio da Z-API (CTWA)** na fase de validação com o Alexis; o match manual é o fallback garantido. |
| D2 | **Investimento realizado** (funil geral e relatórios) = soma dos lançamentos diários `daily_indicators.marketing_investment` do período. Lojas em modo CRM lançam **só esse campo** no dia. | É o único ponto de entrada de investimento definido na spec. |
| D3 | **Funil por campanha** usa o `budget` da campanha como investimento (CAC por campanha = budget ÷ vendas). | Não há lançamento diário por campanha, e metas por campanha foram descartadas na reunião. |
| D4 | **Sinaleiro:** verde ≥ 100% da meta, amarelo ≥ 80%, vermelho < 80%, cinza sem meta. | Spec não fixa thresholds; constantes fáceis de ajustar. |
| D5 | **Classificados (modo CRM)** = leads criados no período que alcançaram a etapa CLASSIFICADOS (histórico ou etapa atual ≥) — mesmo critério dos qualificados. | Consistência com a contagem de qualificados já aprovada (spec §6.5). |
| D6 | **Sinaleiros/metas** só quando a consulta é de **1 loja** e o período cabe em **1 mês** (metas são mensais por loja); caso contrário, cinza. | Evita comparar meta mensal com períodos arbitrários. |

> Crie os `__init__.py` de `src/modules/marketing/` e subpastas (`domain`, `application`, `infrastructure`, `interface`) e de `tests/unit/marketing/` no início.

---

## Task 1: Domínio — funil de custos (`build_cost_funnel`) + `unit_cost`/`traffic_light`

**Files:**
- Modify: `src/modules/metrics/domain/metrics_core.py` (adicionar `unit_cost` e `traffic_light`)
- Create: `src/modules/marketing/domain/cost_funnel.py`
- Test: `tests/unit/marketing/test_cost_funnel.py`

- [ ] **Step 1: Teste (as fórmulas da planilha do Alexis)**

`tests/unit/marketing/test_cost_funnel.py`:
```python
from src.modules.marketing.domain.cost_funnel import build_cost_funnel
from src.modules.metrics.domain.metrics_core import traffic_light, unit_cost

Q = {"leads": 200, "classified": 160, "qualified": 112, "scheduled": 56, "attended": 40, "sales": 8}


def test_cpl_and_cac() -> None:
    f = build_cost_funnel(Q, investment=10000, revenue=125000)
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["unit_cost"] == 50.0          # CPL = 10000/200
    assert stages["sales"]["unit_cost"] == 1250.0        # CAC = 10000/8


def test_conversion_rates() -> None:
    f = build_cost_funnel(Q, investment=10000, revenue=125000)
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["conversion_from_previous"] is None
    assert stages["classified"]["conversion_from_previous"] == 80.0   # 160/200
    assert stages["qualified"]["conversion_from_previous"] == 70.0    # 112/160


def test_roas_roi() -> None:
    f = build_cost_funnel(Q, investment=10000, revenue=125000)
    assert f["roas"] == 12.5
    assert f["roi"] == 11.5


def test_zero_investment_safe() -> None:
    f = build_cost_funnel(Q, investment=0, revenue=125000)
    assert all(s["unit_cost"] is None for s in f["stages"])
    assert f["roas"] is None and f["roi"] is None


def test_unit_cost_and_light() -> None:
    assert unit_cost(1000, 0) is None
    assert unit_cost(1000, 4) == 250.0
    assert traffic_light(100, 100) == "green"
    assert traffic_light(85, 100) == "yellow"
    assert traffic_light(50, 100) == "red"
    assert traffic_light(50, 0) == "gray"
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
uv run pytest tests/unit/marketing/test_cost_funnel.py
```
Expected: FALHA (módulos não existem).

- [ ] **Step 3: Implementar**

Adicione ao fim de `src/modules/metrics/domain/metrics_core.py`:
```python
def unit_cost(investment: float | None, qty: int) -> float | None:
    inv = float(investment or 0)
    return (inv / qty) if inv > 0 and qty > 0 else None


def traffic_light(value: float, goal: float | None) -> str:
    """verde >=100% da meta, amarelo >=80%, vermelho <80%, cinza sem meta."""
    g = float(goal or 0)
    if g <= 0:
        return "gray"
    pct = value / g * 100
    if pct >= 100:
        return "green"
    if pct >= 80:
        return "yellow"
    return "red"
```
`src/modules/marketing/domain/cost_funnel.py`:
```python
from src.modules.metrics.domain.metrics_core import unit_cost

STAGE_ORDER = ["leads", "classified", "qualified", "scheduled", "attended", "sales"]
STAGE_LABELS = {"leads": "Leads", "classified": "Classificados", "qualified": "Qualificados",
                "scheduled": "Agendados", "attended": "Comparecidos", "sales": "Vendas"}


def build_cost_funnel(quantities: dict, investment: float | None, revenue: float) -> dict:
    inv = float(investment or 0)
    stages: list[dict] = []
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
```

- [ ] **Step 4: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/marketing/test_cost_funnel.py
git add -A && git commit -m "feat(marketing): add cost funnel domain (CPL/CAC/ROAS/ROI)"
```

---

## Task 2: Campanhas — entidade, ORM, repositório, CRUD, router

**Files:**
- Create: `src/modules/marketing/domain/entities.py`
- Create: `src/modules/marketing/infrastructure/orm.py`, `repository.py`
- Create: `src/modules/marketing/application/campaigns_crud.py`
- Create: `src/modules/marketing/interface/schemas.py`, `deps.py`, `router.py`
- Modify: `src/main.py`
- Test: `tests/e2e/test_campaigns.py`

- [ ] **Step 1: Entidade + ORM**

`src/modules/marketing/domain/entities.py`:
```python
from dataclasses import dataclass


@dataclass
class Campaign:
    id: str
    store_id: str
    name: str
    started_at: str            # YYYY-MM-DD
    ended_at: str | None       # None = ativa
    budget: float | None
    link_code: str | None
```
`src/modules/marketing/infrastructure/orm.py`:
```python
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class CampaignModel(Base):
    __tablename__ = "marketing_campaigns"
    id: Mapped[str] = mapped_column(primary_key=True)
    store_id: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    link_code: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[date] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Repositório**

`src/modules/marketing/infrastructure/repository.py`:
```python
import uuid
from datetime import date
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.marketing.domain.entities import Campaign
from src.modules.marketing.infrastructure.orm import CampaignModel
from src.shared.domain.errors import NotFoundError


def _to_domain(r: CampaignModel) -> Campaign:
    return Campaign(id=str(r.id), store_id=str(r.store_id), name=r.name,
                    started_at=r.started_at.isoformat(),
                    ended_at=r.ended_at.isoformat() if r.ended_at else None,
                    budget=float(r.budget) if r.budget is not None else None,
                    link_code=r.link_code)


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_store(self, store_id: str) -> list[Campaign]:
        rows = (await self._session.execute(
            select(CampaignModel).where(CampaignModel.store_id == store_id).order_by(CampaignModel.started_at.desc())
        )).scalars().all()
        return [_to_domain(r) for r in rows]

    async def list_in_period(self, store_id: str, start: str, end: str) -> list[Campaign]:
        """Ativas ou encerradas dentro do período (spec: 'ativa ou encerrada no período')."""
        rows = (await self._session.execute(
            select(CampaignModel).where(
                CampaignModel.store_id == store_id,
                CampaignModel.started_at <= date.fromisoformat(end),
                or_(CampaignModel.ended_at.is_(None), CampaignModel.ended_at >= date.fromisoformat(start)),
            ).order_by(CampaignModel.started_at.desc())
        )).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get(self, campaign_id: str) -> Campaign | None:
        r = await self._session.get(CampaignModel, campaign_id)
        return _to_domain(r) if r else None

    async def create(self, data: dict) -> Campaign:
        row = CampaignModel(id=str(uuid.uuid4()),
                            store_id=data["store_id"], name=data["name"],
                            link_code=data.get("link_code"),
                            started_at=date.fromisoformat(data["started_at"]),
                            ended_at=date.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
                            budget=data.get("budget"))
        self._session.add(row)
        await self._session.flush()
        return _to_domain(row)

    async def update(self, campaign_id: str, data: dict) -> Campaign:
        row = await self._session.get(CampaignModel, campaign_id)
        if row is None:
            raise NotFoundError("Campanha não encontrada")
        if "name" in data and data["name"] is not None:
            row.name = data["name"]
        if "link_code" in data:
            row.link_code = data["link_code"]
        if "budget" in data:
            row.budget = data["budget"]
        if "started_at" in data and data["started_at"]:
            row.started_at = date.fromisoformat(data["started_at"])
        if "ended_at" in data:
            row.ended_at = date.fromisoformat(data["ended_at"]) if data["ended_at"] else None
        await self._session.flush()
        return _to_domain(row)

    async def active_with_link_code(self, store_id: str) -> list[Campaign]:
        rows = (await self._session.execute(
            select(CampaignModel).where(CampaignModel.store_id == store_id,
                                        CampaignModel.link_code.isnot(None),
                                        CampaignModel.ended_at.is_(None))
        )).scalars().all()
        return [_to_domain(r) for r in rows]
```

- [ ] **Step 3: Use cases + schemas + router**

`src/modules/marketing/application/campaigns_crud.py`:
```python
from src.modules.marketing.domain.entities import Campaign


class ListCampaignsUseCase:
    def __init__(self, campaigns) -> None:
        self._campaigns = campaigns

    async def execute(self, store_id: str) -> list[Campaign]:
        return await self._campaigns.list_for_store(store_id)


class CreateCampaignUseCase:
    def __init__(self, campaigns) -> None:
        self._campaigns = campaigns

    async def execute(self, data: dict) -> Campaign:
        return await self._campaigns.create(data)


class UpdateCampaignUseCase:
    def __init__(self, campaigns) -> None:
        self._campaigns = campaigns

    async def execute(self, campaign_id: str, data: dict) -> Campaign:
        return await self._campaigns.update(campaign_id, data)
```
`src/modules/marketing/interface/schemas.py`:
```python
from pydantic import BaseModel


class CreateCampaignRequest(BaseModel):
    store_id: str
    name: str
    started_at: str            # YYYY-MM-DD
    ended_at: str | None = None
    budget: float | None = None
    link_code: str | None = None


class UpdateCampaignRequest(BaseModel):
    name: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    budget: float | None = None
    link_code: str | None = None


class CampaignResponse(BaseModel):
    id: str
    store_id: str
    name: str
    started_at: str
    ended_at: str | None
    budget: float | None
    link_code: str | None
```
`src/modules/marketing/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.marketing.application.campaigns_crud import CreateCampaignUseCase, ListCampaignsUseCase, UpdateCampaignUseCase
from src.modules.marketing.infrastructure.repository import CampaignRepository
from src.shared.infrastructure.database import get_session


def _campaigns(session: AsyncSession = Depends(get_session)) -> CampaignRepository:
    return CampaignRepository(session)


def get_list_campaigns_uc(repo: CampaignRepository = Depends(_campaigns)) -> ListCampaignsUseCase:
    return ListCampaignsUseCase(repo)


def get_create_campaign_uc(repo: CampaignRepository = Depends(_campaigns)) -> CreateCampaignUseCase:
    return CreateCampaignUseCase(repo)


def get_update_campaign_uc(repo: CampaignRepository = Depends(_campaigns)) -> UpdateCampaignUseCase:
    return UpdateCampaignUseCase(repo)
```
`src/modules/marketing/interface/router.py` (a parte de campanhas; as rotas do funil entram nas Tasks 6–7):
```python
from fastapi import APIRouter, Depends, Query
from src.modules.marketing.application.campaigns_crud import CreateCampaignUseCase, ListCampaignsUseCase, UpdateCampaignUseCase
from src.modules.marketing.domain.entities import Campaign
from src.modules.marketing.interface.deps import get_create_campaign_uc, get_list_campaigns_uc, get_update_campaign_uc
from src.modules.marketing.interface.schemas import CampaignResponse, CreateCampaignRequest, UpdateCampaignRequest
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(tags=["marketing"])


def _resp(c: Campaign) -> CampaignResponse:
    return CampaignResponse(id=c.id, store_id=c.store_id, name=c.name, started_at=c.started_at,
                            ended_at=c.ended_at, budget=c.budget, link_code=c.link_code)


@router.get("/campaigns")
async def list_campaigns(store_id: str = Query(...), _: CurrentUser = Depends(get_current_user),
                         uc: ListCampaignsUseCase = Depends(get_list_campaigns_uc)) -> list[CampaignResponse]:
    return [_resp(c) for c in await uc.execute(store_id)]


@router.post("/campaigns", status_code=201)
async def create_campaign(body: CreateCampaignRequest, _: CurrentUser = Depends(get_current_user),
                          uc: CreateCampaignUseCase = Depends(get_create_campaign_uc)) -> CampaignResponse:
    return _resp(await uc.execute(body.model_dump()))


@router.patch("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, body: UpdateCampaignRequest, _: CurrentUser = Depends(get_current_user),
                          uc: UpdateCampaignUseCase = Depends(get_update_campaign_uc)) -> CampaignResponse:
    return _resp(await uc.execute(campaign_id, body.model_dump(exclude_unset=True)))
```
Em `src/main.py`, inclua `from src.modules.marketing.interface.router import router as marketing_router` e `app.include_router(marketing_router)`.

- [ ] **Step 4: e2e + commit**

`tests/e2e/test_campaigns.py`:
```python
import pytest


async def _admin(client):
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_and_list_campaign(client) -> None:
    headers = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja MKT"}, headers=headers)).json()
    created = await client.post("/campaigns", json={"store_id": store["id"], "name": "Carro Popular Julho",
                                                    "started_at": "2026-07-01", "budget": 10000}, headers=headers)
    assert created.status_code == 201
    listed = await client.get(f"/campaigns?store_id={store['id']}", headers=headers)
    assert any(c["name"] == "Carro Popular Julho" for c in listed.json())
```
```bash
uv run pytest tests/e2e/test_campaigns.py && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(marketing): add campaigns crud"
```

---

## Task 3: `InvestmentReader` (investimento acumulado do período)

**Files:**
- Create: `src/modules/metrics/infrastructure/investment_reader.py`

- [ ] **Step 1: Implementar (soma `daily_indicators.marketing_investment` — decisão D2)**

`src/modules/metrics/infrastructure/investment_reader.py`:
```python
from datetime import date
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.indicators.infrastructure.orm import DailyIndicatorModel


class InvestmentReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total(self, store_ids: list[str], start: str, end: str) -> float:
        if not store_ids:
            return 0.0
        stmt = select(func.coalesce(func.sum(DailyIndicatorModel.marketing_investment), 0)).where(
            DailyIndicatorModel.store_id.in_(store_ids),
            DailyIndicatorModel.reference_date >= date.fromisoformat(start),
            DailyIndicatorModel.reference_date <= date.fromisoformat(end),
        )
        return float((await self._session.execute(stmt)).scalar_one())
```

- [ ] **Step 2: Commit**

```bash
uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): add investment reader"
```

---

## Task 4: Relatório CRM — classificados + custos + filtro por campanha + investimento

**Files:**
- Modify: `src/modules/metrics/domain/metrics_core.py` (substituir `aggregate_by_origin_for_range` e `build_report_processed`)
- Modify: `src/modules/metrics/application/reports.py`, `interface/{deps.py,router.py}`
- Test: Modify `tests/unit/metrics/test_metrics_core.py` (adicionar testes)

- [ ] **Step 1: Testes novos (adicione ao `tests/unit/metrics/test_metrics_core.py`)**

```python
def test_by_origin_classified() -> None:
    by = aggregate_by_origin_for_range([lead()], "2026-02-01", "2026-02-28",
                                       passed_qualificados=None, passed_classificados=lambda l: True)
    assert by["receptivo"]["classified"] == 1


def test_report_costs() -> None:
    from src.modules.metrics.domain.metrics_core import build_report_processed
    leads = [lead(), lead(fechou_negocio=True, data_fechou_negocio="2026-02-12", rentabilidade=5000)]
    res = build_report_processed(leads, "2026-02-01", "2026-02-28",
                                 passed_qualificados=None, passed_classificados=lambda l: True, investment=1000)
    assert res["investment"] == 1000
    assert res["costs"]["cost_per_lead"] == 500.0        # 1000 / 2 leads receptivos
    assert res["costs"]["cac"] == 1000.0                 # 1000 / 1 venda
    assert res["summary"]["classified"] == 2
```

- [ ] **Step 2: Rodar e ver falhar → substituir as duas funções em `metrics_core.py`**

Substitua `aggregate_by_origin_for_range` e `build_report_processed` por:
```python
def aggregate_by_origin_for_range(leads: list[dict], start: str, end: str,
                                  passed_qualificados=None, passed_classificados=None) -> dict:
    def empty() -> dict:
        return {"total": 0, "classified": 0, "qualified": 0, "scheduled": 0, "attended": 0, "converted": 0, "revenue": 0.0}
    by = {"receptivo": empty(), "prospeccao": empty(), "outros": empty()}
    for lead in leads:
        b = by[normalize_funil_key(lead.get("funil"))]
        if ymd_in_range(to_local_ymd(lead.get("created_at")), start, end):
            b["total"] += 1
            if passed_classificados and passed_classificados(lead):
                b["classified"] += 1
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


def build_report_processed(leads: list[dict], start: str, end: str,
                           passed_qualificados=None, passed_classificados=None,
                           investment: float | None = None) -> dict:
    by = aggregate_by_origin_for_range(leads, start, end, passed_qualificados, passed_classificados)
    total_converted = sum(by[o]["converted"] for o in by)
    total_revenue = sum(by[o]["revenue"] for o in by)
    inv = float(investment or 0)
    r = by["receptivo"]  # custos só sobre o funil receptivo (prospecção não tem investimento de mídia)
    costs = {
        "cost_per_lead": unit_cost(inv, r["total"]),
        "cost_per_classified": unit_cost(inv, r["classified"]),
        "cost_per_qualified": unit_cost(inv, r["qualified"]),
        "cost_per_scheduled": unit_cost(inv, r["scheduled"]),
        "cost_per_attended": unit_cost(inv, r["attended"]),
        "cac": unit_cost(inv, r["converted"]),
    }
    return {
        "summary": {
            "totalLeads": sum(by[o]["total"] for o in by),
            "classified": sum(by[o]["classified"] for o in by),
            "qualified": sum(by[o]["qualified"] for o in by),
            "scheduled": sum(by[o]["scheduled"] for o in by),
            "attended": sum(by[o]["attended"] for o in by),
            "converted": total_converted,
            "revenue": total_revenue,
            "avgTicket": (total_revenue / total_converted) if total_converted > 0 else 0.0,
        },
        "byOrigin": by,
        "costs": costs,
        "investment": inv,
    }
```
> `unit_cost` já está no módulo (Task 1). A ordem das funções no arquivo não importa (são top-level).

- [ ] **Step 3: `ReportUseCase` com classificados, investimento e filtro por campanha**

Substitua `src/modules/metrics/application/reports.py` por:
```python
from src.modules.metrics.domain.metrics_core import build_report_processed


class ReportUseCase:
    def __init__(self, reader, stage_reach, investment) -> None:
        self._reader = reader
        self._stage_reach = stage_reach
        self._investment = investment

    async def execute(self, store_ids: list[str], start: str, end: str, campaign_id: str | None = None) -> dict:
        leads = await self._reader.leads_for_stores(store_ids)
        if campaign_id:
            leads = [l for l in leads if str(l.get("campaign_id") or "") == campaign_id]
        q_ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        c_ctx = await self._stage_reach.build(store_ids, "CLASSIFICADOS")
        inv = await self._investment.total(store_ids, start, end)
        return build_report_processed(leads, start, end, q_ctx.passed, c_ctx.passed, inv)
```
Em `src/modules/metrics/interface/deps.py`, atualize o provider:
```python
from src.modules.metrics.infrastructure.investment_reader import InvestmentReader
def get_report_uc(session: AsyncSession = Depends(get_session)) -> ReportUseCase:
    return ReportUseCase(MetricsLeadReader(session), StageReachReader(session), InvestmentReader(session))
```
Em `src/modules/metrics/interface/router.py`, adicione o parâmetro na rota `reports`:
```python
@router.get("/reports")
async def reports(store_id: str | None = Query(None), start: str = Query(...), end: str = Query(...),
                  campaign_id: str | None = Query(None),
                  user: CurrentUser = Depends(get_current_user), uc: ReportUseCase = Depends(get_report_uc),
                  access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc)) -> dict:
    return await uc.execute(await _resolve(user, store_id, access), start, end, campaign_id)
```
> Se o `_resolve` do seu router já recebe `stores` (Plano 08b Task 4), mantenha essa assinatura — só acrescente `campaign_id`.

- [ ] **Step 4: Rodar tudo + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): report with classified, costs and campaign filter"
```

---

## Task 5: Relatório modo indicadores — classificados + investimento na comparação de metas

**Files:**
- Modify: `src/modules/metrics/domain/indicators_report.py` (substituição completa)
- Modify: `src/modules/metrics/application/indicators_report.py`
- Test: Modify `tests/unit/metrics/test_indicators_report.py` (adicionar teste)

- [ ] **Step 1: Teste novo (adicione ao arquivo de teste)**

```python
def test_classified_investment_and_costs() -> None:
    indicators = [ind(origin="receptivo", total_leads=10, classified_leads=8, converted_leads=2,
                      profitability=1000, daily_expenses=0, marketing_investment=500)]
    goals = [{"origin": "receptivo", "conversions_quantity": 5, "profitability_goal": 3000,
              "marketing_investment_goal": 600}]
    res = build_indicators_report(indicators, goals)
    assert res["summary"]["classified"] == 8
    assert res["investment"] == 500
    assert res["costs"]["cost_per_lead"] == 50.0
    assert res["costs"]["cac"] == 250.0
    gc = res["goalsComparison"][0]
    assert gc["Meta Investimento"] == 600 and gc["Real Investimento"] == 500
```
> Atualize também a função `ind(**o)` do arquivo para incluir `"classified_leads": 0, "marketing_investment": 0` no dicionário base.

- [ ] **Step 2: Rodar e ver falhar → substituir `indicators_report.py`**

`src/modules/metrics/domain/indicators_report.py` (substituição completa):
```python
from src.modules.metrics.domain.metrics_core import unit_cost


def net_profitability(ind: dict) -> float:
    return float(ind.get("profitability") or 0) - float(ind.get("daily_expenses") or 0)


_LABEL = {"receptivo": "Receptivo", "prospeccao": "Prospecção", "outros": "Outros"}


def build_indicators_report(indicators: list[dict], goals: list[dict]) -> dict:
    def empty() -> dict:
        return {"total": 0, "classified": 0, "qualified": 0, "scheduled": 0, "attended": 0, "converted": 0, "revenue": 0.0}
    by = {"receptivo": empty(), "prospeccao": empty(), "outros": empty()}
    investment = 0.0
    for ind in indicators:
        investment += float(ind.get("marketing_investment") or 0)
        o = ind.get("origin")
        if o not in by:
            continue
        if o == "receptivo":
            by[o]["total"] += ind.get("total_leads") or 0
            by[o]["classified"] += ind.get("classified_leads") or 0
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
        origin_investment = sum(float(i.get("marketing_investment") or 0) for i in origin_inds)
        goals_comparison.append({
            "origin": _LABEL.get(goal.get("origin"), "Outros"),
            "Meta Conversões": goal.get("conversions_quantity") or 0,
            "Real Conversões": conversions,
            "Meta Receita": float(goal.get("profitability_goal") or 0),
            "Real Receita": revenue,
            "Meta Investimento": float(goal.get("marketing_investment_goal") or 0),
            "Real Investimento": origin_investment,
        })

    total_converted = sum(by[o]["converted"] for o in by)
    total_revenue = sum(by[o]["revenue"] for o in by)
    r = by["receptivo"]  # custos só sobre o receptivo
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
```
> Regras preservadas do front: `totalLeads`/`qualified` (e agora `classified`) contam **só receptivo**; `revenue` é líquida (bruto − despesas). O teste antigo `test_net_revenue_and_receptivo_only_total` continua passando.

- [ ] **Step 3: Rodar tudo + commit**

```bash
uv run pytest tests/unit/metrics/test_indicators_report.py && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): indicators report with classified, investment and costs"
```

---

## Task 6: Funil de marketing geral — `GET /marketing/funnel` (Seção 1 da tela nova)

**Files:**
- Create: `src/modules/marketing/application/marketing_funnel.py`
- Modify: `src/modules/marketing/interface/deps.py`, `router.py`
- Test: `tests/unit/marketing/test_marketing_funnel.py`

- [ ] **Step 1: Teste com fakes**

`tests/unit/marketing/test_marketing_funnel.py`:
```python
import pytest
from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase


def lead(**o):
    base = {"id": "l1", "created_at": "2026-07-10T12:00:00Z", "funil": "receptivo", "stage_id": None,
            "campaign_id": None, "data_agendamento": None, "hora_agendamento": None,
            "data_marcacao_agendamento": None, "compareceu_agendamento": False, "data_compareceu": None,
            "fechou_negocio": False, "data_fechou_negocio": None, "rentabilidade": None}
    base.update(o)
    return base


class FakeReader:
    def __init__(self, leads): self.leads = leads
    async def leads_for_stores(self, ids): return self.leads


class FakeReach:
    async def build(self, ids, stage):  # todo lead 'passou' por qualquer etapa
        return type("C", (), {"passed": staticmethod(lambda l: True)})()


class FakeInvestment:
    async def total(self, ids, start, end): return 1000.0


class FakeCampaigns:
    async def get(self, cid): return type("C", (), {"id": cid, "budget": 400.0})()


class FakeGoals:
    async def list(self, store_id, year, month):
        return [{"origin": "receptivo", "leads_quantity": 2, "conversions_quantity": 1,
                 "marketing_investment_goal": 1200}]


def make(leads):
    return MarketingFunnelUseCase(FakeReader(leads), FakeReach(), FakeInvestment(), FakeCampaigns(), FakeGoals())


@pytest.mark.asyncio
async def test_receptivo_only_and_costs() -> None:
    leads = [lead(), lead(id="l2", funil="prospeccao_ativa")]   # prospecção fica de fora
    f = await make(leads).execute(["s1"], "2026-07-01", "2026-07-31")
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["quantity"] == 1
    assert stages["leads"]["unit_cost"] == 1000.0


@pytest.mark.asyncio
async def test_campaign_filter_uses_budget() -> None:
    leads = [lead(campaign_id="camp1"), lead(id="l2")]
    f = await make(leads).execute(["s1"], "2026-07-01", "2026-07-31", campaign_id="camp1")
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["quantity"] == 1
    assert f["investment"] == 400.0                       # budget da campanha (D3)


@pytest.mark.asyncio
async def test_lights_from_goals() -> None:
    f = await make([lead()]).execute(["s1"], "2026-07-01", "2026-07-31")
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["light"] == "red"              # 1 de meta 2 = 50%
    assert stages["classified"]["light"] == "gray"        # classificados não tem meta
    assert f["investment_goal"] == 1200.0
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/marketing/application/marketing_funnel.py`:
```python
from src.modules.marketing.domain.cost_funnel import build_cost_funnel
from src.modules.metrics.domain.metrics_core import (aggregate_totals_for_range, normalize_funil_key,
                                                     to_local_ymd, traffic_light, ymd_in_range)

_GOAL_FIELD = {"leads": "leads_quantity", "qualified": "qualified_quantity",
               "scheduled": "scheduled_quantity", "attended": "attended_quantity",
               "sales": "conversions_quantity"}


class MarketingFunnelUseCase:
    def __init__(self, reader, stage_reach, investment, campaigns, goals) -> None:
        self._reader = reader
        self._stage_reach = stage_reach
        self._investment = investment
        self._campaigns = campaigns
        self._goals = goals

    async def execute(self, store_ids: list[str], start: str, end: str, campaign_id: str | None = None) -> dict:
        leads = await self._reader.leads_for_stores(store_ids)
        receptive = [l for l in leads if normalize_funil_key(l.get("funil")) == "receptivo"]
        if campaign_id:
            receptive = [l for l in receptive if str(l.get("campaign_id") or "") == campaign_id]

        c_ctx = await self._stage_reach.build(store_ids, "CLASSIFICADOS")
        q_ctx = await self._stage_reach.build(store_ids, "QUALIFICADOS")
        totals = aggregate_totals_for_range(receptive, start, end, q_ctx.passed)
        classified = sum(1 for l in receptive
                         if ymd_in_range(to_local_ymd(l.get("created_at")), start, end) and c_ctx.passed(l))
        quantities = {"leads": totals["total_leads"], "classified": classified,
                      "qualified": totals["qualified_leads"], "scheduled": totals["scheduled"],
                      "attended": totals["attended"], "sales": totals["conversions"]}

        if campaign_id:
            camp = await self._campaigns.get(campaign_id)
            investment = float(camp.budget or 0) if camp else 0.0     # D3: budget da campanha
        else:
            investment = await self._investment.total(store_ids, start, end)   # D2: lançamentos diários

        funnel = build_cost_funnel(quantities, investment, totals["total_revenue"])
        await self._apply_lights(funnel, store_ids, start, end, campaign_id)
        return funnel

    async def _apply_lights(self, funnel: dict, store_ids: list[str], start: str, end: str,
                            campaign_id: str | None) -> None:
        same_month = start[:7] == end[:7]
        if campaign_id or len(store_ids) != 1 or not same_month:    # D6
            for st in funnel["stages"]:
                st["goal"] = None
                st["pct_of_goal"] = None
                st["light"] = "gray"
            funnel["investment_goal"] = None
            return
        goals = await self._goals.list(store_ids[0], int(start[:4]), int(start[5:7]))
        receptivo_goal = next((g for g in goals if g.get("origin") == "receptivo"), None) or {}
        for st in funnel["stages"]:
            field = _GOAL_FIELD.get(st["stage"])
            goal = float(receptivo_goal.get(field) or 0) if field else 0.0
            st["goal"] = goal or None
            st["pct_of_goal"] = (st["quantity"] / goal * 100) if goal > 0 else None
            st["light"] = traffic_light(st["quantity"], goal)
        inv_goal = float(receptivo_goal.get("marketing_investment_goal") or 0)
        funnel["investment_goal"] = inv_goal or None
```

- [ ] **Step 3: Rota + wiring**

Em `src/modules/marketing/interface/deps.py`, adicione:
```python
from src.modules.goals.infrastructure.repository import GoalRepository
from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase
from src.modules.metrics.infrastructure.investment_reader import InvestmentReader
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.metrics.infrastructure.stage_reach_reader import StageReachReader


def get_marketing_funnel_uc(session: AsyncSession = Depends(get_session)) -> MarketingFunnelUseCase:
    return MarketingFunnelUseCase(MetricsLeadReader(session), StageReachReader(session),
                                  InvestmentReader(session), CampaignRepository(session), GoalRepository(session))
```
> O import de `GoalRepository` segue o Plano 09 (repositório com `list(store_id, year, month) -> list[dict]`). Se o caminho/nome real divergir ao executar, alinhe **no Plano 09**, não aqui.

Em `src/modules/marketing/interface/router.py`, adicione (as rotas de marketing **exigem** `store_id`; o escopo é validado):
```python
from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase
from src.modules.marketing.interface.deps import get_marketing_funnel_uc
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.modules.metrics.interface.deps import get_accessible_uc
from src.shared.domain.errors import ForbiddenError


async def _check_scope(user: CurrentUser, store_id: str, access: GetAccessibleStoreIdsUseCase) -> None:
    scope = await access.execute(user)
    if scope is not None and store_id not in scope:
        raise ForbiddenError("Loja fora do escopo.")


@router.get("/marketing/funnel")
async def marketing_funnel(store_id: str = Query(...), start: str = Query(...), end: str = Query(...),
                           campaign_id: str | None = Query(None),
                           user: CurrentUser = Depends(get_current_user),
                           uc: MarketingFunnelUseCase = Depends(get_marketing_funnel_uc),
                           access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc)) -> dict:
    await _check_scope(user, store_id, access)
    return await uc.execute([store_id], start, end, campaign_id)
```

- [ ] **Step 4: Rodar tudo + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(marketing): general receptive cost funnel endpoint"
```

---

## Task 7: Funil por campanha — `GET /marketing/by-campaign` (Seções 2 e 3)

**Files:**
- Create: `src/modules/marketing/application/campaigns_funnels.py`
- Modify: `src/modules/marketing/interface/deps.py`, `router.py`

- [ ] **Step 1: Use case (um funil por campanha ativa/encerrada no período)**

`src/modules/marketing/application/campaigns_funnels.py`:
```python
from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase


class CampaignsFunnelsUseCase:
    def __init__(self, funnel_uc: MarketingFunnelUseCase, campaigns) -> None:
        self._funnel_uc = funnel_uc
        self._campaigns = campaigns

    async def execute(self, store_id: str, start: str, end: str) -> list[dict]:
        out: list[dict] = []
        for camp in await self._campaigns.list_in_period(store_id, start, end):
            funnel = await self._funnel_uc.execute([store_id], start, end, campaign_id=camp.id)
            out.append({"campaign": {"id": camp.id, "name": camp.name, "started_at": camp.started_at,
                                     "ended_at": camp.ended_at, "budget": camp.budget},
                        "funnel": funnel})
        return out
```
> A Seção 3 (gráfico de comparação) usa este mesmo payload — o front plota leads/vendas/CAC/ROAS por campanha a partir da lista.

- [ ] **Step 2: Rota + wiring + commit**

Em `deps.py`:
```python
from src.modules.marketing.application.campaigns_funnels import CampaignsFunnelsUseCase


def get_campaigns_funnels_uc(session: AsyncSession = Depends(get_session)) -> CampaignsFunnelsUseCase:
    return CampaignsFunnelsUseCase(get_marketing_funnel_uc(session), CampaignRepository(session))
```
> Nota: chamar `get_marketing_funnel_uc(session)` direto funciona porque o provider só precisa da session.

Em `router.py`:
```python
from src.modules.marketing.application.campaigns_funnels import CampaignsFunnelsUseCase
from src.modules.marketing.interface.deps import get_campaigns_funnels_uc


@router.get("/marketing/by-campaign")
async def marketing_by_campaign(store_id: str = Query(...), start: str = Query(...), end: str = Query(...),
                                user: CurrentUser = Depends(get_current_user),
                                uc: CampaignsFunnelsUseCase = Depends(get_campaigns_funnels_uc),
                                access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc)) -> list[dict]:
    await _check_scope(user, store_id, access)
    return await uc.execute(store_id, start, end)
```
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(marketing): per-campaign funnels endpoint"
```

---

## Task 8: Projeções — trio Meta / Realizado / Projetando + sinaleiro

**Files:**
- Modify: `src/modules/metrics/application/projections.py` (substituição completa)
- Modify: `src/modules/metrics/interface/deps.py`
- Test: `tests/unit/metrics/test_projections.py`

- [ ] **Step 1: Teste com fakes**

`tests/unit/metrics/test_projections.py`:
```python
import pytest
from src.modules.metrics.application.projections import ProjectionsUseCase


class FakeReader:
    async def leads_for_stores(self, ids):
        return [{"id": "l1", "created_at": "2026-07-05T12:00:00Z", "funil": "receptivo", "stage_id": None,
                 "data_agendamento": None, "hora_agendamento": None, "data_marcacao_agendamento": None,
                 "compareceu_agendamento": False, "data_compareceu": None,
                 "fechou_negocio": True, "data_fechou_negocio": "2026-07-05", "rentabilidade": 1000}]


class FakeWorkdays:
    def working_days_in_month(self, y, m): return 26
    def remaining_working_days(self, y, m, d): return 13


class FakeReach:
    async def build(self, ids, stage):
        return type("C", (), {"passed": staticmethod(lambda l: False)})()


class FakeGoals:
    async def list(self, store_id, year, month):
        return [{"origin": "receptivo", "leads_quantity": 10, "qualified_quantity": 0, "scheduled_quantity": 0,
                 "attended_quantity": 0, "conversions_quantity": 2, "profitability_goal": 5000,
                 "marketing_investment_goal": 0}]


@pytest.mark.asyncio
async def test_projection_trio_and_light() -> None:
    uc = ProjectionsUseCase(FakeReader(), FakeWorkdays(), FakeReach(), FakeGoals())
    res = await uc.execute(["s1"], 2026, 7)
    conv = next(m for m in res["metrics"] if m["key"] == "conversions")
    assert conv["goal"] == 2 and conv["actual"] == 1
    assert conv["projected"] == 2.0            # 1 + (1/13)*13
    assert conv["light"] == "green"            # projetando bater a meta
    assert res["working_days"] == {"total": 26, "elapsed": 13, "remaining": 13}
```

- [ ] **Step 2: Rodar e ver falhar → substituir `projections.py`**

`src/modules/metrics/application/projections.py` (substituição completa):
```python
from calendar import monthrange
from datetime import date
from src.modules.metrics.domain.metrics_core import aggregate_totals_for_range, traffic_light
from src.modules.metrics.domain.working_days import WorkingDays

_METRICS = [("leads", "total_leads", "leads_quantity"),
            ("qualified", "qualified_leads", "qualified_quantity"),
            ("scheduled", "scheduled", "scheduled_quantity"),
            ("attended", "attended", "attended_quantity"),
            ("conversions", "conversions", "conversions_quantity"),
            ("revenue", "total_revenue", "profitability_goal")]


class ProjectionsUseCase:
    def __init__(self, reader, workdays: WorkingDays, stage_reach, goals) -> None:
        self._reader = reader
        self._workdays = workdays
        self._stage_reach = stage_reach
        self._goals = goals

    async def execute(self, store_ids: list[str], year: int, month: int) -> dict:
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
        if len(store_ids) == 1:
            for g in await self._goals.list(store_ids[0], year, month):   # soma entre origens
                for _, _, gf in _METRICS:
                    goals_row[gf] = goals_row.get(gf, 0.0) + float(g.get(gf) or 0)

        metrics = []
        for key, tf, gf in _METRICS:
            actual = float(totals[tf])
            pace = actual / elapsed if elapsed > 0 else 0.0
            projected = round(actual + pace * remaining, 2)
            goal = goals_row.get(gf, 0.0)
            metrics.append({"key": key, "goal": goal or None, "actual": actual, "projected": projected,
                            "pct_of_goal": (projected / goal * 100) if goal > 0 else None,
                            "light": traffic_light(projected, goal)})
        return {"working_days": {"total": total_wd, "elapsed": elapsed, "remaining": remaining},
                "metrics": metrics}
```
Em `src/modules/metrics/interface/deps.py`, atualize o provider:
```python
from src.modules.goals.infrastructure.repository import GoalRepository
def get_projections_uc(session: AsyncSession = Depends(get_session)) -> ProjectionsUseCase:
    return ProjectionsUseCase(MetricsLeadReader(session), WorkingDays(), StageReachReader(session), GoalRepository(session))
```
> A resposta muda de formato (`{totals, working_days, projected_conversions}` → `{working_days, metrics}`); a rota não muda. É a tela nova de Projeções (spec: só ajustes de leitura, a lógica de dias úteis fica igual).

- [ ] **Step 3: Rodar tudo + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(metrics): projections with goal/actual/projected trio and lights"
```

---

## Task 9: CRM — bloqueio de avanço sem campanha (`require_campaign_on_lead`)

**Files:**
- Create: `src/modules/crm/infrastructure/store_flags.py`
- Modify: `src/modules/crm/application/move_lead.py` (substituição completa)
- Modify: o provider do move no `crm/interface/deps.py`
- Test: `tests/unit/crm/test_move_lead_campaign.py`

- [ ] **Step 1: Teste**

`tests/unit/crm/test_move_lead_campaign.py`:
```python
import pytest
from src.modules.crm.application.move_lead import MoveLeadStageUseCase
from src.modules.crm.domain.stage_rules import StageRules
from src.shared.domain.errors import DomainError


class FakeLeads:
    def __init__(self, lead): self.lead = lead; self.moved_to = None
    async def get_or_raise(self, lead_id): return self.lead
    async def update(self, lead_id, data): self.moved_to = data["stage_id"]; return {**self.lead, **data}


class FakeStages:
    def __init__(self, stages): self.stages = stages
    async def get(self, sid): return next(type("S", (), s)() for s in self.stages if s["id"] == sid)
    async def list_for_funnel(self, fid): return [type("S", (), s)() for s in self.stages]


class FakeHistory:
    async def record(self, lead_id, stage_id): ...


class FakeActivity:
    async def log(self, **kw): ...


class FlagsOn:
    async def require_campaign(self, store_id): return True


class U:
    user_id = "u1"; role = "client"


STAGES = [{"id": "st0", "name": "RECEBIDOS", "funnel_id": "f1", "sort_order": 0},
          {"id": "st1", "name": "CLASSIFICADOS", "funnel_id": "f1", "sort_order": 1}]
BASE = {"id": "l1", "store_id": "s1", "stage_id": "st0", "funil": "receptivo",
        "telefone": "1", "nome": "A", "cidade": "C", "campaign_id": None}


def make(lead):
    return MoveLeadStageUseCase(FakeLeads(lead), FakeStages(STAGES), FakeHistory(), FakeActivity(),
                                StageRules(), store_flags=FlagsOn())


@pytest.mark.asyncio
async def test_blocks_receptivo_without_campaign() -> None:
    with pytest.raises(DomainError, match="campanha"):
        await make(dict(BASE)).execute("l1", "st1", U())


@pytest.mark.asyncio
async def test_allows_with_campaign() -> None:
    uc = make({**BASE, "campaign_id": "camp1"})
    moved = await uc.execute("l1", "st1", U())
    assert moved["stage_id"] == "st1"


@pytest.mark.asyncio
async def test_prospeccao_not_blocked() -> None:
    uc = make({**BASE, "funil": "prospeccao_ativa"})
    moved = await uc.execute("l1", "st1", U())
    assert moved["stage_id"] == "st1"
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/crm/infrastructure/store_flags.py`:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.stores.infrastructure.orm import StoreModel


class StoreFlagsReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def require_campaign(self, store_id: str) -> bool:
        row = await self._session.get(StoreModel, store_id)
        return bool(row and row.require_campaign_on_lead)
```
`src/modules/crm/application/move_lead.py` (substituição completa — a novidade é o parâmetro opcional `store_flags` e o bloqueio; o resto é idêntico ao Plano 05):
```python
from src.modules.crm.domain.stage_rules import StageRules
from src.shared.domain.errors import DomainError


def _is_receptivo(funil: object) -> bool:
    f = funil.strip() if isinstance(funil, str) else funil
    return (not f) or f == "receptivo"


class MoveLeadStageUseCase:
    def __init__(self, leads, stages, history, activity, rules: StageRules, store_flags=None) -> None:
        self._leads = leads
        self._stages = stages
        self._history = history
        self._activity = activity
        self._rules = rules
        self._store_flags = store_flags

    async def execute(self, lead_id: str, to_stage_id: str, user) -> dict:
        lead = await self._leads.get_or_raise(lead_id)
        target = await self._stages.get(to_stage_id)
        if target is None:
            raise DomainError("Etapa de destino inválida.")
        ordered = await self._stages.list_for_funnel(target.funnel_id)
        ids = [str(s.id) for s in ordered]
        from_i = ids.index(str(lead["stage_id"])) if str(lead["stage_id"]) in ids else -1
        to_i = ids.index(to_stage_id)
        if to_i > from_i:
            if (self._store_flags is not None and _is_receptivo(lead.get("funil"))
                    and not lead.get("campaign_id")
                    and await self._store_flags.require_campaign(lead["store_id"])):
                raise DomainError("Preencha a campanha de marketing do lead antes de avançar.")
            stages_for_rules = [{"name": s.name} for s in ordered]
            ok, missing = self._rules.can_advance(stages_for_rules, from_i, to_i, lead)
            if not ok:
                labels = ", ".join(dict.fromkeys(m["label"] for m in missing))
                raise DomainError(f"Preencha os campos obrigatórios: {labels}.")
        moved = await self._leads.update(lead_id, {"stage_id": to_stage_id})
        await self._history.record(lead_id, to_stage_id)
        await self._activity.log(store_id=lead["store_id"], actor_user_id=user.user_id,
                                 action="lead_moved", entity_type="lead", entity_id=lead_id)
        return moved
```
No provider do move em `crm/interface/deps.py`, injete o flag reader:
```python
from src.modules.crm.infrastructure.store_flags import StoreFlagsReader
# no provider do MoveLeadStageUseCase, acrescente o último argumento:
#   MoveLeadStageUseCase(..., StageRules(), store_flags=StoreFlagsReader(session))
```
> Os testes do Plano 05 continuam passando: `store_flags` tem default `None` (sem flag, sem bloqueio). O `campaign_id` do lead é editável pelo `PATCH /crm/leads/{id}` existente (preenchimento manual pela pré-vendas); a flag da loja é editável pelo `PATCH /admin/stores/{id}` existente (`{"require_campaign_on_lead": true}`).

- [ ] **Step 3: Rodar tudo + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(crm): block stage advance without campaign when store requires it"
```

---

## Task 10: Webhook — auto-match de campanha no lead receptivo

**Files:**
- Create: `src/modules/marketing/domain/campaign_match.py`
- Create: `src/modules/marketing/infrastructure/matcher.py`
- Modify: `src/modules/webhook/application/handle_zapi.py`, `interface/deps.py`, teste do webhook
- Test: `tests/unit/marketing/test_campaign_match.py`

- [ ] **Step 1: Teste da função pura**

`tests/unit/marketing/test_campaign_match.py`:
```python
from src.modules.marketing.domain.campaign_match import match_campaign_by_link

CAMPS = [{"id": "c1", "link_code": "carro-popular-julho"}, {"id": "c2", "link_code": "suv-agosto"}]


def test_match_by_referral() -> None:
    body = {"referral": {"sourceUrl": "https://wa.me/55449?text=carro-popular-julho"}}
    assert match_campaign_by_link(CAMPS, body) == "c1"


def test_match_by_text() -> None:
    body = {"text": {"message": "Olá! Vi o anúncio suv-agosto e quero saber mais"}}
    assert match_campaign_by_link(CAMPS, body) == "c2"


def test_no_match() -> None:
    assert match_campaign_by_link(CAMPS, {"text": {"message": "oi"}}) is None
    assert match_campaign_by_link([], {"text": {"message": "carro-popular-julho"}}) is None
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/marketing/domain/campaign_match.py`:
```python
def _collect_haystack(body: dict) -> str:
    parts: list[str] = []
    referral = body.get("referral")
    if isinstance(referral, dict):
        parts.extend(str(v) for v in referral.values() if v)
    text = body.get("text")
    if isinstance(text, dict):
        parts.append(str(text.get("message") or ""))
    for key in ("message", "sourceUrl", "adSourceUrl", "ctwaClid"):
        v = body.get(key)
        if v:
            parts.append(str(v))
    return " ".join(parts)


def match_campaign_by_link(campaigns: list[dict], body: dict) -> str | None:
    """Melhor esforço (decisão D1): procura o link_code de cada campanha ativa no payload."""
    hay = _collect_haystack(body)
    if not hay:
        return None
    for c in campaigns:
        code = c.get("link_code")
        if code and code in hay:
            return str(c["id"])
    return None
```
`src/modules/marketing/infrastructure/matcher.py`:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.marketing.domain.campaign_match import match_campaign_by_link
from src.modules.marketing.infrastructure.repository import CampaignRepository


class CampaignMatcher:
    def __init__(self, session: AsyncSession) -> None:
        self._campaigns = CampaignRepository(session)

    async def match(self, store_id: str, body: dict) -> str | None:
        camps = await self._campaigns.active_with_link_code(store_id)
        return match_campaign_by_link([{"id": c.id, "link_code": c.link_code} for c in camps], body)
```

- [ ] **Step 3: Integrar no webhook**

Em `src/modules/webhook/application/handle_zapi.py`:
1. Constructor ganha o matcher (último parâmetro): `def __init__(self, stores, leads, funnels, stages, leads_count, users, history, phone, round_robin, campaign_matcher=None)` e `self._campaign_matcher = campaign_matcher`.
2. No `execute`, logo antes do `lead = await self._leads.create({...})`, adicione:
```python
        campaign_id = None
        if self._campaign_matcher is not None:
            campaign_id = await self._campaign_matcher.match(store.id, body)
```
3. E inclua `"campaign_id": campaign_id,` no dicionário do `create` (junto de `"funil": "receptivo"`).

Em `src/modules/webhook/interface/deps.py`, injete no final da construção:
```python
from src.modules.marketing.infrastructure.matcher import CampaignMatcher
# ... no get_handle_zapi_uc, acrescente o último argumento:
#     CampaignMatcher(session)
```
No teste `tests/unit/webhook/test_handle_zapi.py`, os fakes não passam matcher (default `None`) — nada quebra. Adicione um caso com matcher:
```python
class MatcherHit:
    async def match(self, store_id, body): return "camp1"


@pytest.mark.asyncio
async def test_creates_lead_with_campaign() -> None:
    leads = Leads()
    uc = HandleZapiWebhookUseCase(Stores(), leads, Funnels(), Stages(), LeadsCount(), Users(), History(),
                                  Phone(), RoundRobin(), campaign_matcher=MatcherHit())
    await uc.execute("tok", {"phone": "5544999999999@c.us"})
    assert leads.created["campaign_id"] == "camp1"
```

- [ ] **Step 4: Rodar tudo + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(webhook): auto-match marketing campaign on inbound lead"
```

---

## Task 11: Verificação final + concluir

- [ ] **Step 1: Suíte completa verde**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
```
Expected: tudo verde.

- [ ] **Step 2: Smoke manual dos endpoints novos (local)**

```bash
docker compose up -d db && uv run uvicorn src.main:app --port 3001 &
# login → criar loja → criar campanha → GET /marketing/funnel?store_id=...&start=2026-07-01&end=2026-07-31
# GET /marketing/by-campaign?... e GET /metrics/reports?...&campaign_id=...
```
Expected: JSONs com `stages` (6 etapas), `costs`, `roas`/`roi`, `lights`.

- [ ] **Step 3: Commit final + status**

```bash
git add -A && git commit -m "feat(marketing): complete marketing module"
```
Atualize o status do Plano 10b para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Cobertura da spec (checklist)

| Item da spec (`MUDANCAS_MARKETING_RELATORIOS.md`) | Onde |
|---|---|
| Entidade Campanha (store_id, name, started_at, ended_at, budget) | Task 2 |
| `campaign_id` no lead (auto + manual) | Task 10 (auto) + `PATCH /crm/leads/{id}` existente (manual) |
| `marketing_investment_goal` nas metas | Plano 09 (revisado) + Tasks 5/6/8 |
| `marketing_investment` no lançamento diário | Plano 09 (revisado) + Tasks 3/5 |
| Linha CLASSIFICADOS (CRM + indicadores) | Tasks 4/5/6 (`classified_leads` no Plano 09) |
| Coluna de custos (CPL…CAC) nos relatórios | Tasks 4/5 |
| Filtro por campanha no relatório | Task 4 |
| Tela Marketing nova — Seção 1 (funil geral + ROAS/ROI + sinaleiros) | Task 6 |
| Seções 2 e 3 (funil por campanha + comparação) | Task 7 |
| Projeções: Meta/Realizado/Projetando + sinaleiro + % da meta | Task 8 |
| Flag `require_campaign_on_lead` + bloqueio no Kanban | Task 9 (+ Plano 04 revisado) |
| Prospecção ativa fora do funil de custos | Tasks 4/6 (filtro receptivo) |
| Dashboard sem alteração | — (nada mexido) |

## Resultado

- Backend completo do módulo de marketing: campanhas, funil de custos com CPL/CAC/ROAS/ROI e sinaleiros, filtro por campanha, investimento em metas/indicadores, classificados, projeções com trio e bloqueio configurável por campanha. As 3 seções da tela nova de Marketing têm API pronta.

**Próximo:** [`11-cleanup-cutover.md`](./11-cleanup-cutover.md).
