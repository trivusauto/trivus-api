# Plano 09 — Leads legado, Indicadores, Metas e Planos (código completo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–04. Código copia-e-cola.

**Goal:** CRUD do modo "indicadores" e administrativos — `leads` legado, `daily_indicators` (upsert), `goals`, `action_plans`. Campos confirmados no front (`reference_date`, `daily_expenses`, `conversions_quantity`, status `a_fazer|em_andamento|concluido`). Spec §4.4–4.7.

**Architecture:** Quatro módulos hexagonais simples. Padrão do Plano 04.

> Crie os `__init__.py` de cada módulo e subpastas, e das pastas de teste correspondentes.

---

## Task 1: Leads legado

**Files:** `src/modules/legacy_leads/infrastructure/orm.py`, `repository.py`, `application/use_cases.py`, `interface/{schemas.py,deps.py,router.py}`, `src/main.py`, `tests/e2e/test_legacy_leads.py`

- [ ] **Step 1: ORM + repositório**

`src/modules/legacy_leads/infrastructure/orm.py`:
```python
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class LegacyLeadModel(Base):
    __tablename__ = "leads"
    id: Mapped[str] = mapped_column(primary_key=True)
    store_id: Mapped[str] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    car: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    origin: Mapped[str | None] = mapped_column(String, nullable=True)
    origin_custom: Mapped[str | None] = mapped_column(String, nullable=True)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    qualified: Mapped[bool] = mapped_column(Boolean, default=False)
    disqualified: Mapped[bool] = mapped_column(Boolean, default=False)
    disqualification_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    attended: Mapped[bool] = mapped_column(Boolean, default=False)
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    profitability: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```
`src/modules/legacy_leads/infrastructure/repository.py`:
```python
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.legacy_leads.infrastructure.orm import LegacyLeadModel


def _to_dict(r: LegacyLeadModel) -> dict:
    d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["id"] = str(d["id"])
    for k in ("entry_date", "created_at", "updated_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    if d.get("profitability") is not None:
        d["profitability"] = float(d["profitability"])
    return d


class LegacyLeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_store(self, store_id: str) -> list[dict]:
        rows = (await self._session.execute(select(LegacyLeadModel).where(LegacyLeadModel.store_id == store_id).order_by(LegacyLeadModel.created_at.desc()))).scalars().all()
        return [_to_dict(r) for r in rows]

    async def create(self, data: dict) -> dict:
        if data.get("entry_date"):
            data = {**data, "entry_date": date.fromisoformat(data["entry_date"])}
        row = LegacyLeadModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return _to_dict(row)

    async def update(self, lead_id: str, data: dict) -> dict:
        row = await self._session.get(LegacyLeadModel, lead_id)
        for k, v in data.items():
            setattr(row, k, v)
        row.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return _to_dict(row)

    async def delete(self, lead_id: str) -> None:
        await self._session.execute(delete(LegacyLeadModel).where(LegacyLeadModel.id == lead_id))
```

- [ ] **Step 2: Use cases + schemas + router**

`src/modules/legacy_leads/application/use_cases.py`:
```python
class ListLegacyLeadsUseCase:
    def __init__(self, repo): self._repo = repo
    async def execute(self, store_id: str) -> list[dict]: return await self._repo.list_for_store(store_id)


class CreateLegacyLeadUseCase:
    def __init__(self, repo): self._repo = repo
    async def execute(self, data: dict) -> dict: return await self._repo.create(data)


class UpdateLegacyLeadUseCase:
    def __init__(self, repo): self._repo = repo
    async def execute(self, lead_id: str, data: dict) -> dict: return await self._repo.update(lead_id, data)


class DeleteLegacyLeadUseCase:
    def __init__(self, repo): self._repo = repo
    async def execute(self, lead_id: str) -> None: await self._repo.delete(lead_id)
```
`src/modules/legacy_leads/interface/schemas.py`:
```python
from pydantic import BaseModel


class CreateLegacyLeadRequest(BaseModel):
    store_id: str
    name: str | None = None
    phone: str | None = None
    car: str | None = None
    city: str | None = None
    origin: str | None = None
    origin_custom: str | None = None
    entry_date: str | None = None


class UpdateLegacyLeadRequest(BaseModel):
    qualified: bool | None = None
    disqualified: bool | None = None
    disqualification_reason: str | None = None
    scheduled: bool | None = None
    attended: bool | None = None
    converted: bool | None = None
    profitability: float | None = None
```
`src/modules/legacy_leads/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.legacy_leads.application.use_cases import (CreateLegacyLeadUseCase, DeleteLegacyLeadUseCase, ListLegacyLeadsUseCase, UpdateLegacyLeadUseCase)
from src.modules.legacy_leads.infrastructure.repository import LegacyLeadRepository
from src.shared.infrastructure.database import get_session


def _repo(session: AsyncSession = Depends(get_session)) -> LegacyLeadRepository:
    return LegacyLeadRepository(session)


def list_uc(r: LegacyLeadRepository = Depends(_repo)) -> ListLegacyLeadsUseCase: return ListLegacyLeadsUseCase(r)
def create_uc(r: LegacyLeadRepository = Depends(_repo)) -> CreateLegacyLeadUseCase: return CreateLegacyLeadUseCase(r)
def update_uc(r: LegacyLeadRepository = Depends(_repo)) -> UpdateLegacyLeadUseCase: return UpdateLegacyLeadUseCase(r)
def delete_uc(r: LegacyLeadRepository = Depends(_repo)) -> DeleteLegacyLeadUseCase: return DeleteLegacyLeadUseCase(r)
```
`src/modules/legacy_leads/interface/router.py`:
```python
from fastapi import APIRouter, Body, Depends, Query
from src.modules.legacy_leads.interface.deps import create_uc, delete_uc, list_uc, update_uc
from src.modules.legacy_leads.interface.schemas import CreateLegacyLeadRequest, UpdateLegacyLeadRequest
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(prefix="/leads", tags=["legacy-leads"])


@router.get("")
async def list_leads(store_id: str = Query(...), _: CurrentUser = Depends(get_current_user), uc=Depends(list_uc)) -> list[dict]:
    return await uc.execute(store_id)


@router.post("", status_code=201)
async def create_lead(body: CreateLegacyLeadRequest, _: CurrentUser = Depends(get_current_user), uc=Depends(create_uc)) -> dict:
    return await uc.execute(body.model_dump(exclude_none=True))


@router.patch("/{lead_id}")
async def update_lead(lead_id: str, body: UpdateLegacyLeadRequest, _: CurrentUser = Depends(get_current_user), uc=Depends(update_uc)) -> dict:
    return await uc.execute(lead_id, body.model_dump(exclude_none=True))


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: str, _: CurrentUser = Depends(get_current_user), uc=Depends(delete_uc)) -> None:
    await uc.execute(lead_id)
```
Em `src/main.py`, inclua `from src.modules.legacy_leads.interface.router import router as legacy_leads_router` e `app.include_router(legacy_leads_router)`.

- [ ] **Step 3: e2e + commit**

`tests/e2e/test_legacy_leads.py`: login admin, cria loja, `POST /leads` (store_id + name + origin=receptivo) → 201, `GET /leads?store_id=` contém o lead.
```bash
uv run pytest tests/e2e/test_legacy_leads.py && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(legacy): add legacy leads module"
```

---

## Task 2: Indicadores (upsert)

**Files:** `src/modules/indicators/infrastructure/{orm.py,repository.py}`, `application/use_cases.py`, `interface/{schemas.py,deps.py,router.py}`, `tests/integration/test_indicators_repository.py`

- [ ] **Step 1: ORM**

`src/modules/indicators/infrastructure/orm.py`:
```python
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class DailyIndicatorModel(Base):
    __tablename__ = "daily_indicators"
    id: Mapped[str] = mapped_column(primary_key=True)
    store_id: Mapped[str] = mapped_column(String)
    reference_date: Mapped[date] = mapped_column(Date)
    origin: Mapped[str] = mapped_column(String)
    origin_custom: Mapped[str | None] = mapped_column(String, nullable=True)
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    qualified_leads: Mapped[int] = mapped_column(Integer, default=0)
    classified_leads: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_leads: Mapped[int] = mapped_column(Integer, default=0)
    attended_leads: Mapped[int] = mapped_column(Integer, default=0)
    converted_leads: Mapped[int] = mapped_column(Integer, default=0)
    profitability: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    daily_expenses: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    marketing_investment: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Repositório com upsert**

`src/modules/indicators/infrastructure/repository.py`:
```python
import uuid
from datetime import date
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.indicators.infrastructure.orm import DailyIndicatorModel


def _to_dict(r: DailyIndicatorModel) -> dict:
    d = {c.name: getattr(r, c.name) for c in r.__table__.columns}
    d["id"] = str(d["id"])
    d["reference_date"] = d["reference_date"].isoformat()
    if d.get("created_at") is not None:
        d["created_at"] = d["created_at"].isoformat()
    for k in ("profitability", "daily_expenses", "marketing_investment"):
        if d.get(k) is not None:
            d[k] = float(d[k])
    return d


class IndicatorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, store_id: str, date_from: str | None, date_to: str | None) -> list[dict]:
        stmt = select(DailyIndicatorModel).where(DailyIndicatorModel.store_id == store_id)
        if date_from:
            stmt = stmt.where(DailyIndicatorModel.reference_date >= date.fromisoformat(date_from))
        if date_to:
            stmt = stmt.where(DailyIndicatorModel.reference_date <= date.fromisoformat(date_to))
        rows = (await self._session.execute(stmt.order_by(DailyIndicatorModel.reference_date.desc()))).scalars().all()
        return [_to_dict(r) for r in rows]

    async def upsert(self, data: dict) -> None:
        values = {**data, "id": str(uuid.uuid4()), "reference_date": date.fromisoformat(data["reference_date"])}
        stmt = pg_insert(DailyIndicatorModel).values(**values)
        update_cols = {k: v for k, v in values.items() if k not in ("id", "store_id", "reference_date", "origin", "created_at")}
        stmt = stmt.on_conflict_do_update(index_elements=["store_id", "reference_date", "origin"], set_=update_cols)
        await self._session.execute(stmt)
```

- [ ] **Step 3: Teste de integração (upsert não duplica)**

`tests/integration/test_indicators_repository.py`:
```python
import uuid
import pytest
from src.modules.indicators.infrastructure.repository import IndicatorRepository


@pytest.mark.asyncio
async def test_upsert_updates(session) -> None:
    repo = IndicatorRepository(session)
    store = str(uuid.uuid4())
    base = {"store_id": store, "reference_date": "2026-02-10", "origin": "receptivo", "total_leads": 5}
    await repo.upsert(base)
    await repo.upsert({**base, "total_leads": 8})
    rows = await repo.list(store, None, None)
    assert len(rows) == 1 and rows[0]["total_leads"] == 8
```
> `store_id` aqui é um UUID livre (a tabela `daily_indicators` referencia `stores`, mas no teste de integração isolado o registro é criado direto — se a FK exigir loja existente, crie uma via `StoreModel` antes).

- [ ] **Step 4: Use cases + router + commit**

`src/modules/indicators/application/use_cases.py`:
```python
class ListIndicatorsUseCase:
    def __init__(self, repo): self._repo = repo
    async def execute(self, store_id, date_from, date_to): return await self._repo.list(store_id, date_from, date_to)


class UpsertIndicatorUseCase:
    def __init__(self, repo): self._repo = repo
    async def execute(self, data: dict) -> None: await self._repo.upsert(data)
```
Schemas `UpsertIndicatorRequest` (`store_id, reference_date, origin` obrigatórios; contagens `int >= 0` opcionais default 0 — incluindo `classified_leads`; `profitability`, `daily_expenses`, `marketing_investment`, `notes`, `origin_custom` opcionais). Router `GET /indicators?store_id=&from=&to=`, `POST /indicators`. Inclua no `main.py`.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(indicators): add indicators with upsert"
```

---

## Task 3: Metas (`goals`)

**Files:** `src/modules/goals/*`

- [ ] **Step 1: Módulo completo (padrão do Plano 04)**

ORM `GoalModel` (`goals`: id, store_id, month, year, origin, leads_quantity, qualified_quantity, scheduled_quantity, attended_quantity, conversions_quantity, profitability_goal, average_ticket_goal, marketing_investment_goal). O repositório expõe `list(store_id, year, month) -> list[dict]` (o Plano 10b consome essa assinatura). Repositório com `upsert` por `(store_id, year, month, origin)` (índice único do schema-alvo — mesmo padrão da Task 2). Use cases: `ListGoals(store_id, year, month)`, `UpsertGoal(data)`, `DeleteGoal(id)`. Router: `GET /goals?store_id=&year=&month=` (`require_roles("admin","client","shop_user")`), `POST /admin/goals` e `DELETE /admin/goals/{id}` (`require_roles("admin")`). Schemas validam `month 1-12`, `origin` no enum, quantidades `>= 0`.

- [ ] **Step 2: e2e + commit**

`tests/e2e/test_goals.py`: admin cria meta, `GET /goals?store_id=&year=&month=` retorna.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(goals): add goals module"
```

---

## Task 4: Planos de ação (`action_plans`)

**Files:** `src/modules/action_plans/*`

- [ ] **Step 1: Módulo completo**

ORM `ActionPlanModel` (`action_plans`: id, store_id, title, description, status default `a_fazer`, created_at, updated_at). Use cases: `ListActionPlans(store_id)`, `CreateActionPlan(data)` (admin), `UpdateActionPlan(id, data)` (admin), `UpdateStatus(id, status)` (loja), `DeleteActionPlan(id)` (admin). Router: `GET /action-plans?store_id=` (`get_current_user`), `PATCH /action-plans/{id}/status` (loja), `POST/PATCH/DELETE /admin/action-plans` (`require_roles("admin")`). Schema `status` no enum `a_fazer|em_andamento|concluido`.

- [ ] **Step 2: e2e + commit + concluir**

`tests/e2e/test_action_plans.py`: admin cria plano; `PATCH /action-plans/{id}/status` com `{"status":"em_andamento"}` → 200; `GET` reflete.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(action-plans): add action plans module"
```
Atualize o status do Plano 09 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Resultado

- Modo indicadores (leads legado + daily_indicators com upsert), metas e planos via API hexagonal — campos alinhados com as telas.

**Próximo:** [`10-bulk-send.md`](./10-bulk-send.md).
