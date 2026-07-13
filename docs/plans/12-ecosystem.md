# Plano 12 — Ecossistema (empresas, assinaturas, serviços, gates e upsell)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e a spec [`../ECOSSISTEMA_TRIVUS.md`](../ECOSSISTEMA_TRIVUS.md). Conclua 02–10b antes. **Execute após o 10b e antes do 11.** Código copia-e-cola.

**Goal:** Gestão do ecossistema da holding: empresas (`companies`) donas de lojas, planos, assinaturas (manual + trial automático), catálogo de serviços **com CRUD** apontando para **feature keys** (grão módulo/tela/card/área), resolução de acesso (`require_feature` + response-shaping), upsell (interesses + notificação n8n) e integração de cobrança com o **framework de pagamentos do dono** (desenvolvida e desligada).

**Architecture:** Novo módulo hexagonal `ecosystem/`. Regras de resolução são domínio puro. Decisões E1–E7 na spec. Lojas com `company_id NULL` = modo legado sem gate (E6); admin nunca é gateado (E7).

**Tech Stack:** o mesmo do Plano 03.

> Crie os `__init__.py` de `src/modules/ecosystem/` e subpastas (`domain`, `application`, `infrastructure`, `interface`) e de `tests/unit/ecosystem/` no início.

---

## Task 1: Registro de feature keys (domínio puro)

**Files:**
- Create: `src/modules/ecosystem/domain/feature_keys.py`
- Test: `tests/unit/ecosystem/test_feature_keys.py`

- [ ] **Step 1: Teste**

`tests/unit/ecosystem/test_feature_keys.py`:
```python
from src.modules.ecosystem.domain.feature_keys import ALL_FEATURE_KEYS, is_valid_feature_key, list_feature_keys


def test_known_keys_exist() -> None:
    for key in ("crm.kanban", "agenda", "metrics.reports.costs", "bulk_send"):
        assert is_valid_feature_key(key)


def test_invalid_key() -> None:
    assert is_valid_feature_key("nao.existe") is False


def test_list_has_labels() -> None:
    items = list_feature_keys()
    assert all("key" in i and "label" in i and "kind" in i for i in items)
    assert len(items) == len(ALL_FEATURE_KEYS)
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/ecosystem/domain/feature_keys.py`:
```python
"""Registro versionado das feature keys — a verdade do que o código gateia.
Grão livre: módulo, tela, card ou área (convenção modulo.tela.area)."""

ALL_FEATURE_KEYS: dict[str, dict] = {
    "crm.kanban": {"label": "CRM — Kanban de leads", "kind": "tela"},
    "crm.activity_log": {"label": "CRM — Histórico de atividades", "kind": "area"},
    "agenda": {"label": "Agenda", "kind": "tela"},
    "webhook.zapi": {"label": "Captação automática WhatsApp", "kind": "modulo"},
    "metrics.dashboard": {"label": "Dashboard de KPIs", "kind": "tela"},
    "metrics.reports": {"label": "Relatórios por origem", "kind": "tela"},
    "metrics.reports.costs": {"label": "Relatórios — coluna de custos (CPL…CAC)", "kind": "area"},
    "metrics.marketing": {"label": "Marketing — funil de custos", "kind": "tela"},
    "metrics.projections": {"label": "Projeções", "kind": "tela"},
    "metrics.team": {"label": "Performance da equipe", "kind": "tela"},
    "marketing.campaigns": {"label": "Cadastro de campanhas", "kind": "tela"},
    "bulk_send": {"label": "Disparos em massa", "kind": "modulo"},
    "indicators": {"label": "Modo indicadores", "kind": "tela"},
    "goals": {"label": "Metas", "kind": "tela"},
    "action_plans": {"label": "Planos de ação", "kind": "tela"},
}


def is_valid_feature_key(key: str) -> bool:
    return key in ALL_FEATURE_KEYS


def list_feature_keys() -> list[dict]:
    return [{"key": k, **v} for k, v in ALL_FEATURE_KEYS.items()]
```
```bash
uv run pytest tests/unit/ecosystem/test_feature_keys.py
git add -A && git commit -m "feat(ecosystem): add feature keys registry"
```

---

## Task 2: Resolução de entitlements (domínio puro)

**Files:**
- Create: `src/modules/ecosystem/domain/entitlements.py`
- Test: `tests/unit/ecosystem/test_entitlements.py`

- [ ] **Step 1: Teste (a cadeia da spec §3)**

`tests/unit/ecosystem/test_entitlements.py`:
```python
from datetime import date
from src.modules.ecosystem.domain.entitlements import resolve_feature_keys, subscription_usable

TODAY = date(2026, 7, 15)
SERVICES = [
    {"key": "crm_completo", "active": True, "feature_keys": ["crm.kanban", "agenda"]},
    {"key": "metricas_avancadas", "active": True, "feature_keys": ["metrics.marketing", "metrics.projections"]},
    {"key": "consultoria", "active": True, "feature_keys": []},
]


def test_active_subscription_usable() -> None:
    assert subscription_usable({"status": "active"}, TODAY) is True
    assert subscription_usable({"status": "suspended"}, TODAY) is False
    assert subscription_usable(None, TODAY) is False


def test_trial_expires_on_read() -> None:
    assert subscription_usable({"status": "trialing", "trial_ends_at": "2026-07-15"}, TODAY) is True
    assert subscription_usable({"status": "trialing", "trial_ends_at": "2026-07-14"}, TODAY) is False


def test_resolution_chain() -> None:
    sub = {"status": "active"}
    keys = resolve_feature_keys(sub, plan_service_keys=["crm_completo", "metricas_avancadas"],
                                enabled_service_keys=["crm_completo"], services=SERVICES, today=TODAY)
    assert keys == {"crm.kanban", "agenda"}          # metricas permitida no plano mas desligada na loja


def test_unusable_subscription_blocks_all() -> None:
    keys = resolve_feature_keys({"status": "canceled"}, ["crm_completo"], ["crm_completo"], SERVICES, TODAY)
    assert keys == set()
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/ecosystem/domain/entitlements.py`:
```python
from datetime import date


def subscription_usable(sub: dict | None, today: date) -> bool:
    """active sempre; trialing só até trial_ends_at (expira na leitura, sem cron)."""
    if not sub:
        return False
    status = sub.get("status")
    if status == "active":
        return True
    if status == "trialing":
        te = sub.get("trial_ends_at")
        return bool(te and str(te)[:10] >= today.isoformat())
    return False


def resolve_feature_keys(sub: dict | None, plan_service_keys: list[str],
                         enabled_service_keys: list[str], services: list[dict], today: date) -> set[str]:
    """plano permite ∩ ligado na loja → união das feature_keys dos serviços ativos."""
    if not subscription_usable(sub, today):
        return set()
    allowed = set(plan_service_keys or []) & set(enabled_service_keys or [])
    keys: set[str] = set()
    for svc in services:
        if svc.get("key") in allowed and svc.get("active", True):
            keys.update(svc.get("feature_keys") or [])
    return keys
```
```bash
uv run pytest tests/unit/ecosystem/test_entitlements.py
git add -A && git commit -m "feat(ecosystem): add entitlement resolution domain"
```

---

## Task 3: ORM + repositórios

**Files:**
- Create: `src/modules/ecosystem/infrastructure/orm.py`, `repositories.py`

- [ ] **Step 1: ORM (mapeia MODELO_ALVO §17–23)**

`src/modules/ecosystem/infrastructure/orm.py`:
```python
from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class CompanyModel(Base):
    __tablename__ = "companies"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    cnpj: Mapped[str | None] = mapped_column(String, nullable=True)
    responsible_name: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlanModel(Base):
    __tablename__ = "plans"
    id: Mapped[str] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    service_keys: Mapped[list] = mapped_column(JSONB, default=list)
    max_stores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_month: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"
    id: Mapped[str] = mapped_column(primary_key=True)
    company_id: Mapped[str] = mapped_column(String)
    plan_id: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    trial_ends_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_mode: Mapped[str] = mapped_column(String, default="manual")
    gateway_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    gateway_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    canceled_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceModel(Base):
    __tablename__ = "services"
    id: Mapped[str] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    what_it_is: Mapped[str | None] = mapped_column(String, nullable=True)
    what_it_does: Mapped[str | None] = mapped_column(String, nullable=True)
    upsell_pitch: Mapped[str | None] = mapped_column(String, nullable=True)
    feature_keys: Mapped[list] = mapped_column(JSONB, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class StoreServiceModel(Base):
    __tablename__ = "store_services"
    id: Mapped[str] = mapped_column(primary_key=True)
    store_id: Mapped[str] = mapped_column(String)
    service_key: Mapped[str] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ServiceInterestModel(Base):
    __tablename__ = "service_interests"
    id: Mapped[str] = mapped_column(primary_key=True)
    company_id: Mapped[str | None] = mapped_column(String, nullable=True)
    store_id: Mapped[str | None] = mapped_column(String, nullable=True)
    service_key: Mapped[str] = mapped_column(String)
    requested_by: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="novo")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubscriptionPaymentModel(Base):
    __tablename__ = "subscription_payments"
    id: Mapped[str] = mapped_column(primary_key=True)
    subscription_id: Mapped[str] = mapped_column(String)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    gateway: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```
> Lembrete: adicione também a coluna `company_id` no `StoreModel` (Plano 04, `src/modules/stores/infrastructure/orm.py`): `company_id: Mapped[str | None] = mapped_column(String, nullable=True)`.

- [ ] **Step 2: Repositórios**

`src/modules/ecosystem/infrastructure/repositories.py`:
```python
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.ecosystem.infrastructure.orm import (CompanyModel, PlanModel, ServiceInterestModel,
                                                      ServiceModel, StoreServiceModel, SubscriptionModel,
                                                      SubscriptionPaymentModel)
from src.shared.domain.errors import NotFoundError


def _row_to_dict(row) -> dict:
    d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    d["id"] = str(d["id"])
    for k, v in list(d.items()):
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
        elif k.endswith("_id") and v is not None:
            d[k] = str(v)
    return d


class _CrudRepo:
    model: type

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, obj_id: str) -> dict | None:
        row = await self._session.get(self.model, obj_id)
        return _row_to_dict(row) if row else None

    async def get_or_raise(self, obj_id: str) -> dict:
        d = await self.get(obj_id)
        if d is None:
            raise NotFoundError(f"{self.model.__tablename__}: não encontrado")
        return d

    async def create(self, data: dict) -> dict:
        row = self.model(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return _row_to_dict(row)

    async def update(self, obj_id: str, data: dict) -> dict:
        row = await self._session.get(self.model, obj_id)
        if row is None:
            raise NotFoundError(f"{self.model.__tablename__}: não encontrado")
        for k, v in data.items():
            setattr(row, k, v)
        await self._session.flush()
        return _row_to_dict(row)


class CompanyRepository(_CrudRepo):
    model = CompanyModel

    async def list_all(self) -> list[dict]:
        rows = (await self._session.execute(select(CompanyModel).order_by(CompanyModel.name))).scalars().all()
        return [_row_to_dict(r) for r in rows]


class PlanRepository(_CrudRepo):
    model = PlanModel

    async def list_all(self) -> list[dict]:
        rows = (await self._session.execute(select(PlanModel).order_by(PlanModel.name))).scalars().all()
        return [_row_to_dict(r) for r in rows]

    async def get_by_key(self, key: str) -> dict | None:
        row = (await self._session.execute(select(PlanModel).where(PlanModel.key == key))).scalar_one_or_none()
        return _row_to_dict(row) if row else None


class SubscriptionRepository(_CrudRepo):
    model = SubscriptionModel

    async def current_for_company(self, company_id: str) -> dict | None:
        stmt = (select(SubscriptionModel).where(SubscriptionModel.company_id == company_id,
                                                SubscriptionModel.status != "canceled")
                .order_by(SubscriptionModel.created_at.desc()).limit(1))
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _row_to_dict(row) if row else None

    async def list_all(self) -> list[dict]:
        rows = (await self._session.execute(select(SubscriptionModel).order_by(SubscriptionModel.created_at.desc()))).scalars().all()
        return [_row_to_dict(r) for r in rows]


class ServiceRepository(_CrudRepo):
    model = ServiceModel

    async def list_all(self, only_active: bool = False) -> list[dict]:
        stmt = select(ServiceModel).order_by(ServiceModel.sort_order, ServiceModel.name)
        if only_active:
            stmt = stmt.where(ServiceModel.active.is_(True))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_row_to_dict(r) for r in rows]

    async def get_by_key(self, key: str) -> dict | None:
        row = (await self._session.execute(select(ServiceModel).where(ServiceModel.key == key))).scalar_one_or_none()
        return _row_to_dict(row) if row else None


class StoreServiceRepository(_CrudRepo):
    model = StoreServiceModel

    async def enabled_keys_for_store(self, store_id: str) -> list[str]:
        stmt = select(StoreServiceModel.service_key).where(StoreServiceModel.store_id == store_id,
                                                           StoreServiceModel.enabled.is_(True))
        return [str(k) for k in (await self._session.execute(stmt)).scalars().all()]

    async def set_service(self, store_id: str, service_key: str, enabled: bool) -> None:
        stmt = select(StoreServiceModel).where(StoreServiceModel.store_id == store_id,
                                               StoreServiceModel.service_key == service_key)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            self._session.add(StoreServiceModel(id=str(uuid.uuid4()), store_id=store_id,
                                                service_key=service_key, enabled=enabled))
        else:
            row.enabled = enabled
        await self._session.flush()


class ServiceInterestRepository(_CrudRepo):
    model = ServiceInterestModel

    async def list_by_status(self, status: str | None) -> list[dict]:
        stmt = select(ServiceInterestModel).order_by(ServiceInterestModel.created_at.desc())
        if status:
            stmt = stmt.where(ServiceInterestModel.status == status)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_row_to_dict(r) for r in rows]


class SubscriptionPaymentRepository(_CrudRepo):
    model = SubscriptionPaymentModel
```

- [ ] **Step 3: Commit**

```bash
uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(ecosystem): add orm and repositories"
```

---

## Task 4: CRUD de serviços (guarda-corpos) + planos

**Files:**
- Create: `src/modules/ecosystem/application/services_crud.py`, `plans_crud.py`
- Test: `tests/unit/ecosystem/test_services_crud.py`

- [ ] **Step 1: Teste (as regras que protegem o catálogo)**

`tests/unit/ecosystem/test_services_crud.py`:
```python
import pytest
from src.modules.ecosystem.application.services_crud import CreateServiceUseCase, UpdateServiceUseCase, DeactivateServiceUseCase
from src.shared.domain.errors import DomainError


class FakeServices:
    def __init__(self): self.created = None; self.updated = None; self.existing = None
    async def get_by_key(self, key): return self.existing
    async def get_or_raise(self, sid): return {"id": sid, "key": "crm_completo", "active": True}
    async def create(self, data): self.created = data; return {"id": "s1", **data}
    async def update(self, sid, data): self.updated = data; return {"id": sid, **data}


class FakePlans:
    def __init__(self, using=False): self.using = using
    async def list_all(self):
        return [{"id": "p1", "key": "pro", "service_keys": ["crm_completo"] if self.using else []}]


@pytest.mark.asyncio
async def test_create_validates_feature_keys() -> None:
    uc = CreateServiceUseCase(FakeServices())
    with pytest.raises(DomainError, match="feature key"):
        await uc.execute({"key": "x", "name": "X", "type": "software", "feature_keys": ["nao.existe"]})


@pytest.mark.asyncio
async def test_create_rejects_duplicate_key() -> None:
    repo = FakeServices()
    repo.existing = {"id": "s0", "key": "crm_completo"}
    with pytest.raises(DomainError, match="key"):
        await CreateServiceUseCase(repo).execute({"key": "crm_completo", "name": "X", "type": "software", "feature_keys": []})


@pytest.mark.asyncio
async def test_update_cannot_change_key() -> None:
    repo = FakeServices()
    await UpdateServiceUseCase(repo).execute("s1", {"key": "outra", "name": "Novo nome"})
    assert "key" not in repo.updated                     # key imutável: silenciosamente descartada


@pytest.mark.asyncio
async def test_deactivate_blocked_when_in_plan() -> None:
    uc = DeactivateServiceUseCase(FakeServices(), FakePlans(using=True))
    with pytest.raises(DomainError, match="plano"):
        await uc.execute("s1")
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/ecosystem/application/services_crud.py`:
```python
from src.modules.ecosystem.domain.feature_keys import is_valid_feature_key
from src.shared.domain.errors import DomainError

_TYPES = ("software", "humano")


def _validate_feature_keys(keys: list[str]) -> None:
    invalid = [k for k in (keys or []) if not is_valid_feature_key(k)]
    if invalid:
        raise DomainError(f"feature key inválida: {', '.join(invalid)}")


class CreateServiceUseCase:
    def __init__(self, services) -> None:
        self._services = services

    async def execute(self, data: dict) -> dict:
        if data.get("type") not in _TYPES:
            raise DomainError("type deve ser software ou humano")
        _validate_feature_keys(data.get("feature_keys") or [])
        if await self._services.get_by_key(data["key"]):
            raise DomainError("Já existe um serviço com essa key.")
        return await self._services.create(data)


class UpdateServiceUseCase:
    def __init__(self, services) -> None:
        self._services = services

    async def execute(self, service_id: str, data: dict) -> dict:
        data = dict(data)
        data.pop("key", None)                       # key é imutável (planos referenciam por key)
        if "feature_keys" in data:
            _validate_feature_keys(data["feature_keys"] or [])
        return await self._services.update(service_id, data)


class DeactivateServiceUseCase:
    """Soft-delete: bloqueado se o serviço estiver em algum plano."""

    def __init__(self, services, plans) -> None:
        self._services = services
        self._plans = plans

    async def execute(self, service_id: str) -> dict:
        svc = await self._services.get_or_raise(service_id)
        for plan in await self._plans.list_all():
            if svc["key"] in (plan.get("service_keys") or []):
                raise DomainError(f"Serviço está no plano '{plan['key']}' — remova do plano antes de desativar.")
        return await self._services.update(service_id, {"active": False})
```
`src/modules/ecosystem/application/plans_crud.py`:
```python
from src.shared.domain.errors import DomainError


class CreatePlanUseCase:
    def __init__(self, plans, services) -> None:
        self._plans = plans
        self._services = services

    async def _validate_services(self, service_keys: list[str]) -> None:
        for key in service_keys or []:
            if await self._services.get_by_key(key) is None:
                raise DomainError(f"Serviço inexistente no catálogo: {key}")

    async def execute(self, data: dict) -> dict:
        if await self._plans.get_by_key(data["key"]):
            raise DomainError("Já existe um plano com essa key.")
        await self._validate_services(data.get("service_keys") or [])
        return await self._plans.create(data)


class UpdatePlanUseCase:
    def __init__(self, plans, services) -> None:
        self._plans = plans
        self._services = services

    async def execute(self, plan_id: str, data: dict) -> dict:
        data = dict(data)
        data.pop("key", None)
        if "service_keys" in data:
            for key in data["service_keys"] or []:
                if await self._services.get_by_key(key) is None:
                    raise DomainError(f"Serviço inexistente no catálogo: {key}")
        return await self._plans.update(plan_id, data)
```
```bash
uv run pytest tests/unit/ecosystem/test_services_crud.py
git add -A && git commit -m "feat(ecosystem): services and plans crud with guard rails"
```

---

## Task 5: Empresas, assinaturas e serviços por loja (use cases)

**Files:**
- Create: `src/modules/ecosystem/application/companies.py`, `subscriptions.py`, `store_services.py`
- Test: `tests/unit/ecosystem/test_subscriptions.py`

- [ ] **Step 1: Teste (regras: max_stores, toggle fora do plano, trial)**

`tests/unit/ecosystem/test_subscriptions.py`:
```python
import pytest
from src.modules.ecosystem.application.store_services import ToggleStoreServiceUseCase
from src.modules.ecosystem.application.subscriptions import CreateSubscriptionUseCase
from src.shared.domain.errors import DomainError


class FakeSubs:
    def __init__(self, current=None): self.current = current; self.created = None
    async def current_for_company(self, cid): return self.current
    async def create(self, data): self.created = data; return {"id": "sub1", **data}


class FakePlans:
    async def get_or_raise(self, pid):
        return {"id": pid, "key": "pro", "service_keys": ["crm_completo"], "max_stores": 2}


class FakeStoresOfCompany:
    def __init__(self, n): self.n = n
    async def count_stores(self, company_id): return self.n
    async def store_company(self, store_id): return "c1"


@pytest.mark.asyncio
async def test_create_subscription_trialing_requires_trial_end() -> None:
    uc = CreateSubscriptionUseCase(FakeSubs(), FakePlans(), FakeStoresOfCompany(1))
    with pytest.raises(DomainError, match="trial"):
        await uc.execute({"company_id": "c1", "plan_id": "p1", "status": "trialing"})


@pytest.mark.asyncio
async def test_create_subscription_max_stores() -> None:
    uc = CreateSubscriptionUseCase(FakeSubs(), FakePlans(), FakeStoresOfCompany(3))
    with pytest.raises(DomainError, match="lojas"):
        await uc.execute({"company_id": "c1", "plan_id": "p1", "status": "active"})


@pytest.mark.asyncio
async def test_toggle_service_not_in_plan() -> None:
    subs = FakeSubs(current={"id": "s", "status": "active", "plan_id": "p1"})
    uc = ToggleStoreServiceUseCase(None, subs, FakePlans(), FakeStoresOfCompany(1))
    with pytest.raises(DomainError, match="plano"):
        await uc.execute("store1", "metricas_avancadas", True)
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/ecosystem/application/companies.py`:
```python
class ListCompaniesUseCase:
    def __init__(self, companies) -> None:
        self._companies = companies

    async def execute(self) -> list[dict]:
        return await self._companies.list_all()


class CreateCompanyUseCase:
    def __init__(self, companies) -> None:
        self._companies = companies

    async def execute(self, data: dict) -> dict:
        return await self._companies.create(data)


class UpdateCompanyUseCase:
    def __init__(self, companies) -> None:
        self._companies = companies

    async def execute(self, company_id: str, data: dict) -> dict:
        return await self._companies.update(company_id, data)
```
`src/modules/ecosystem/application/subscriptions.py`:
```python
from src.shared.domain.errors import DomainError

_STATUSES = ("trialing", "active", "suspended", "canceled")


class CreateSubscriptionUseCase:
    def __init__(self, subscriptions, plans, company_stores) -> None:
        self._subs = subscriptions
        self._plans = plans
        self._company_stores = company_stores

    async def execute(self, data: dict) -> dict:
        if data.get("status") not in ("trialing", "active"):
            raise DomainError("Assinatura nasce como trialing ou active.")
        if data["status"] == "trialing" and not data.get("trial_ends_at"):
            raise DomainError("Assinatura em trial exige trial_ends_at (E2).")
        plan = await self._plans.get_or_raise(data["plan_id"])
        max_stores = plan.get("max_stores")
        if max_stores is not None:
            n = await self._company_stores.count_stores(data["company_id"])
            if n > max_stores:
                raise DomainError(f"O plano permite {max_stores} lojas; a empresa tem {n}.")
        return await self._subs.create({"billing_mode": "manual", **data})


class ChangeSubscriptionStatusUseCase:
    """suspend / reactivate / cancel — admin manual (v1)."""

    def __init__(self, subscriptions) -> None:
        self._subs = subscriptions

    async def execute(self, subscription_id: str, status: str) -> dict:
        if status not in _STATUSES:
            raise DomainError("Status inválido.")
        return await self._subs.update(subscription_id, {"status": status})


class ChangeSubscriptionPlanUseCase:
    def __init__(self, subscriptions, plans) -> None:
        self._subs = subscriptions
        self._plans = plans

    async def execute(self, subscription_id: str, plan_id: str) -> dict:
        await self._plans.get_or_raise(plan_id)
        return await self._subs.update(subscription_id, {"plan_id": plan_id})
```
`src/modules/ecosystem/application/store_services.py`:
```python
from src.shared.domain.errors import DomainError


class ToggleStoreServiceUseCase:
    """Liga/desliga um serviço numa loja — validado contra o plano da empresa (modelo híbrido)."""

    def __init__(self, store_services, subscriptions, plans, company_stores) -> None:
        self._store_services = store_services
        self._subs = subscriptions
        self._plans = plans
        self._company_stores = company_stores

    async def execute(self, store_id: str, service_key: str, enabled: bool) -> None:
        if enabled:
            company_id = await self._company_stores.store_company(store_id)
            if company_id is None:
                raise DomainError("Loja sem empresa vinculada (modo legado) — vincule a uma empresa antes.")
            sub = await self._subs.current_for_company(company_id)
            if sub is None:
                raise DomainError("Empresa sem assinatura.")
            plan = await self._plans.get_or_raise(sub["plan_id"])
            if service_key not in (plan.get("service_keys") or []):
                raise DomainError(f"O serviço '{service_key}' não faz parte do plano da empresa.")
        await self._store_services.set_service(store_id, service_key, enabled)
```
E o leitor de lojas da empresa, `src/modules/ecosystem/infrastructure/company_stores.py`:
```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.stores.infrastructure.orm import StoreModel


class CompanyStoresReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_stores(self, company_id: str) -> int:
        stmt = select(func.count()).select_from(StoreModel).where(StoreModel.company_id == company_id)
        return int((await self._session.execute(stmt)).scalar_one())

    async def store_company(self, store_id: str) -> str | None:
        row = await self._session.get(StoreModel, store_id)
        return str(row.company_id) if row and row.company_id else None
```
```bash
uv run pytest tests/unit/ecosystem/test_subscriptions.py
git add -A && git commit -m "feat(ecosystem): companies, subscriptions and store service toggles"
```

---

## Task 6: `EntitlementService` + `require_feature` (o gate)

**Files:**
- Create: `src/modules/ecosystem/infrastructure/entitlement_service.py`
- Create: `src/shared/interface/feature_gate.py`
- Modify: `src/shared/domain/errors.py`, `src/shared/interface/error_handlers.py`

- [ ] **Step 1: Erro dedicado (o front usa a key pra renderizar o upsell no lugar)**

Em `src/shared/domain/errors.py`, adicione:
```python
class FeatureLockedError(DomainError):
    def __init__(self, feature_key: str) -> None:
        super().__init__(f"Recurso bloqueado: {feature_key}")
        self.feature_key = feature_key
```
Em `src/shared/interface/error_handlers.py`, registre (403 com a key no corpo):
```python
from src.shared.domain.errors import FeatureLockedError
# dentro de register_error_handlers, adicione:
    async def feature_locked_handler(request: Request, exc: FeatureLockedError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"error": "feature_locked", "feature_key": exc.feature_key})

    app.add_exception_handler(FeatureLockedError, feature_locked_handler)
```

- [ ] **Step 2: `EntitlementService` (infra)**

`src/modules/ecosystem/infrastructure/entitlement_service.py`:
```python
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.ecosystem.domain.entitlements import resolve_feature_keys
from src.modules.ecosystem.domain.feature_keys import ALL_FEATURE_KEYS
from src.modules.ecosystem.infrastructure.repositories import (PlanRepository, ServiceRepository,
                                                               StoreServiceRepository, SubscriptionRepository)
from src.modules.stores.infrastructure.orm import StoreModel


class EntitlementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._subs = SubscriptionRepository(session)
        self._plans = PlanRepository(session)
        self._services = ServiceRepository(session)
        self._store_services = StoreServiceRepository(session)

    async def feature_keys_for_store(self, store_id: str) -> set[str]:
        store = await self._session.get(StoreModel, store_id)
        if store is None:
            return set()
        if store.company_id is None:
            return set(ALL_FEATURE_KEYS)          # E6: loja legada (pré-ETL) = sem gate
        sub = await self._subs.current_for_company(str(store.company_id))
        if sub is None:
            return set()                          # E3: sem assinatura = tudo bloqueado
        plan = await self._plans.get(sub["plan_id"]) or {}
        enabled = await self._store_services.enabled_keys_for_store(store_id)
        services = await self._services.list_all(only_active=True)
        if store.crm_enabled:                     # legado: flag do CRM conta como 'ligado' p/ serviços com keys crm.*
            for svc in services:
                if any(str(k).startswith("crm.") for k in (svc.get("feature_keys") or [])):
                    enabled.append(svc["key"])
        return resolve_feature_keys(sub, plan.get("service_keys") or [], enabled, services, date.today())
```

- [ ] **Step 3: Dependency `require_feature` (admin bypassa — E7)**

`src/shared/interface/feature_gate.py`:
```python
from collections.abc import Callable
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.shared.domain.errors import FeatureLockedError
from src.shared.infrastructure.database import get_session
from src.shared.interface.auth_deps import CurrentUser, get_current_user


def require_feature(feature_key: str) -> Callable:
    async def checker(store_id: str = Query(...),
                      user: CurrentUser = Depends(get_current_user),
                      session: AsyncSession = Depends(get_session)) -> None:
        if user.role == "admin":                  # E7
            return
        from src.modules.ecosystem.infrastructure.entitlement_service import EntitlementService
        keys = await EntitlementService(session).feature_keys_for_store(store_id)
        if feature_key not in keys:
            raise FeatureLockedError(feature_key)
    return checker
```
> O import local evita ciclo `shared → modules` na carga. Rotas que usam o gate precisam ter `store_id` como query param (é o caso de agenda, métricas, marketing, indicadores, metas, planos de ação e listagens do CRM).

- [ ] **Step 4: Commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(ecosystem): entitlement service and feature gate"
```

---

## Task 7: Routers do ecossistema (admin + catálogo + upsell)

**Files:**
- Create: `src/modules/ecosystem/application/catalog.py`, `interests.py`
- Create: `src/modules/ecosystem/infrastructure/interest_notifier.py`
- Create: `src/modules/ecosystem/interface/{schemas.py,deps.py,router.py}`
- Modify: `src/shared/infrastructure/settings.py`, `.env(.example)`, `src/main.py`
- Test: `tests/e2e/test_ecosystem.py`

- [ ] **Step 1: Settings + notificador n8n**

Em `src/shared/infrastructure/settings.py`, adicione ao `Settings`:
```python
    n8n_interest_webhook_url: str | None = None
    billing_gateway_enabled: bool = False
    billing_token: str = "dev-billing-token"
```
E ao `.env`/`.env.example`:
```env
N8N_INTEREST_WEBHOOK_URL=
BILLING_GATEWAY_ENABLED=false
BILLING_TOKEN=dev-billing-token
```
`src/modules/ecosystem/infrastructure/interest_notifier.py`:
```python
import httpx


class InterestNotifier:
    """Notifica o comercial da holding via n8n (best-effort; nunca bloqueia o registro)."""

    def __init__(self, url: str | None) -> None:
        self._url = url

    async def notify(self, interest: dict) -> None:
        if not self._url:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(self._url, json=interest)
        except Exception:
            pass
```

- [ ] **Step 2: Use cases de catálogo e interesse**

`src/modules/ecosystem/application/catalog.py`:
```python
class GetCatalogUseCase:
    """Catálogo p/ a loja: cada serviço com unlocked=True/False + mapa feature_key→serviço que desbloqueia."""

    def __init__(self, services, entitlements) -> None:
        self._services = services
        self._entitlements = entitlements

    async def execute(self, store_id: str) -> dict:
        unlocked_keys = await self._entitlements.feature_keys_for_store(store_id)
        catalog = []
        unlockers: dict[str, dict] = {}
        for svc in await self._services.list_all(only_active=True):
            svc_keys = set(svc.get("feature_keys") or [])
            item = {"key": svc["key"], "name": svc["name"], "type": svc["type"],
                    "what_it_is": svc.get("what_it_is"), "what_it_does": svc.get("what_it_does"),
                    "upsell_pitch": svc.get("upsell_pitch"),
                    "unlocked": bool(svc_keys) and svc_keys.issubset(unlocked_keys)}
            catalog.append(item)
            for fk in svc_keys - unlocked_keys:
                unlockers.setdefault(fk, {"service_key": svc["key"], "name": svc["name"],
                                          "upsell_pitch": svc.get("upsell_pitch")})
        return {"services": catalog, "unlocked_feature_keys": sorted(unlocked_keys), "locked_unlockers": unlockers}
```
`src/modules/ecosystem/application/interests.py`:
```python
class RegisterInterestUseCase:
    def __init__(self, interests, company_stores, notifier) -> None:
        self._interests = interests
        self._company_stores = company_stores
        self._notifier = notifier

    async def execute(self, store_id: str, service_key: str, user_id: str) -> dict:
        company_id = await self._company_stores.store_company(store_id)
        interest = await self._interests.create({"company_id": company_id, "store_id": store_id,
                                                 "service_key": service_key, "requested_by": user_id,
                                                 "status": "novo"})
        await self._notifier.notify(interest)
        return interest
```

- [ ] **Step 3: Schemas + deps + router**

`src/modules/ecosystem/interface/schemas.py`:
```python
from pydantic import BaseModel


class CreateServiceRequest(BaseModel):
    key: str
    name: str
    type: str
    what_it_is: str | None = None
    what_it_does: str | None = None
    upsell_pitch: str | None = None
    feature_keys: list[str] = []
    sort_order: int = 0


class CreatePlanRequest(BaseModel):
    key: str
    name: str
    service_keys: list[str] = []
    max_stores: int | None = None
    price_month: float | None = None


class CreateCompanyRequest(BaseModel):
    name: str
    cnpj: str | None = None
    responsible_name: str | None = None


class CreateSubscriptionRequest(BaseModel):
    company_id: str
    plan_id: str
    status: str
    trial_ends_at: str | None = None
    notes: str | None = None


class ToggleStoreServiceRequest(BaseModel):
    service_key: str
    enabled: bool


class RegisterInterestRequest(BaseModel):
    store_id: str
    service_key: str
```
`src/modules/ecosystem/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.ecosystem.application.catalog import GetCatalogUseCase
from src.modules.ecosystem.application.companies import CreateCompanyUseCase, ListCompaniesUseCase, UpdateCompanyUseCase
from src.modules.ecosystem.application.interests import RegisterInterestUseCase
from src.modules.ecosystem.application.plans_crud import CreatePlanUseCase, UpdatePlanUseCase
from src.modules.ecosystem.application.services_crud import CreateServiceUseCase, DeactivateServiceUseCase, UpdateServiceUseCase
from src.modules.ecosystem.application.store_services import ToggleStoreServiceUseCase
from src.modules.ecosystem.application.subscriptions import (ChangeSubscriptionPlanUseCase,
                                                             ChangeSubscriptionStatusUseCase,
                                                             CreateSubscriptionUseCase)
from src.modules.ecosystem.infrastructure.company_stores import CompanyStoresReader
from src.modules.ecosystem.infrastructure.entitlement_service import EntitlementService
from src.modules.ecosystem.infrastructure.interest_notifier import InterestNotifier
from src.modules.ecosystem.infrastructure.repositories import (CompanyRepository, PlanRepository,
                                                               ServiceInterestRepository, ServiceRepository,
                                                               StoreServiceRepository, SubscriptionRepository)
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.settings import get_settings


def get_create_service_uc(s: AsyncSession = Depends(get_session)) -> CreateServiceUseCase:
    return CreateServiceUseCase(ServiceRepository(s))


def get_update_service_uc(s: AsyncSession = Depends(get_session)) -> UpdateServiceUseCase:
    return UpdateServiceUseCase(ServiceRepository(s))


def get_deactivate_service_uc(s: AsyncSession = Depends(get_session)) -> DeactivateServiceUseCase:
    return DeactivateServiceUseCase(ServiceRepository(s), PlanRepository(s))


def get_create_plan_uc(s: AsyncSession = Depends(get_session)) -> CreatePlanUseCase:
    return CreatePlanUseCase(PlanRepository(s), ServiceRepository(s))


def get_update_plan_uc(s: AsyncSession = Depends(get_session)) -> UpdatePlanUseCase:
    return UpdatePlanUseCase(PlanRepository(s), ServiceRepository(s))


def get_companies_ucs(s: AsyncSession = Depends(get_session)) -> tuple:
    repo = CompanyRepository(s)
    return ListCompaniesUseCase(repo), CreateCompanyUseCase(repo), UpdateCompanyUseCase(repo)


def get_create_subscription_uc(s: AsyncSession = Depends(get_session)) -> CreateSubscriptionUseCase:
    return CreateSubscriptionUseCase(SubscriptionRepository(s), PlanRepository(s), CompanyStoresReader(s))


def get_change_sub_status_uc(s: AsyncSession = Depends(get_session)) -> ChangeSubscriptionStatusUseCase:
    return ChangeSubscriptionStatusUseCase(SubscriptionRepository(s))


def get_change_sub_plan_uc(s: AsyncSession = Depends(get_session)) -> ChangeSubscriptionPlanUseCase:
    return ChangeSubscriptionPlanUseCase(SubscriptionRepository(s), PlanRepository(s))


def get_toggle_store_service_uc(s: AsyncSession = Depends(get_session)) -> ToggleStoreServiceUseCase:
    return ToggleStoreServiceUseCase(StoreServiceRepository(s), SubscriptionRepository(s),
                                     PlanRepository(s), CompanyStoresReader(s))


def get_catalog_uc(s: AsyncSession = Depends(get_session)) -> GetCatalogUseCase:
    return GetCatalogUseCase(ServiceRepository(s), EntitlementService(s))


def get_register_interest_uc(s: AsyncSession = Depends(get_session)) -> RegisterInterestUseCase:
    return RegisterInterestUseCase(ServiceInterestRepository(s), CompanyStoresReader(s),
                                   InterestNotifier(get_settings().n8n_interest_webhook_url))


def get_interests_repo(s: AsyncSession = Depends(get_session)) -> ServiceInterestRepository:
    return ServiceInterestRepository(s)


def get_subs_repo(s: AsyncSession = Depends(get_session)) -> SubscriptionRepository:
    return SubscriptionRepository(s)


def get_entitlements(s: AsyncSession = Depends(get_session)) -> EntitlementService:
    return EntitlementService(s)
```
`src/modules/ecosystem/interface/router.py`:
```python
from fastapi import APIRouter, Body, Depends, Query
from src.modules.ecosystem.domain.feature_keys import list_feature_keys
from src.modules.ecosystem.interface.deps import (get_catalog_uc, get_change_sub_plan_uc, get_change_sub_status_uc,
                                                  get_companies_ucs, get_create_plan_uc, get_create_service_uc,
                                                  get_create_subscription_uc, get_deactivate_service_uc,
                                                  get_entitlements, get_interests_repo, get_register_interest_uc,
                                                  get_subs_repo, get_toggle_store_service_uc, get_update_plan_uc,
                                                  get_update_service_uc)
from src.modules.ecosystem.interface.schemas import (CreateCompanyRequest, CreatePlanRequest, CreateServiceRequest,
                                                     CreateSubscriptionRequest, RegisterInterestRequest,
                                                     ToggleStoreServiceRequest)
from src.shared.interface.auth_deps import CurrentUser, get_current_user
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["ecosystem"])

# ---------- público autenticado ----------

@router.get("/ecosystem/feature-keys")
async def feature_keys(_: CurrentUser = Depends(require_roles("admin"))) -> list[dict]:
    return list_feature_keys()


@router.get("/ecosystem/services")
async def catalog(store_id: str = Query(...), _: CurrentUser = Depends(get_current_user),
                  uc=Depends(get_catalog_uc)) -> dict:
    return await uc.execute(store_id)


@router.get("/ecosystem/my-entitlements")
async def my_entitlements(store_id: str = Query(...), _: CurrentUser = Depends(get_current_user),
                          ent=Depends(get_entitlements)) -> dict:
    return {"feature_keys": sorted(await ent.feature_keys_for_store(store_id))}


@router.post("/ecosystem/interests", status_code=201)
async def register_interest(body: RegisterInterestRequest, user: CurrentUser = Depends(get_current_user),
                            uc=Depends(get_register_interest_uc)) -> dict:
    return await uc.execute(body.store_id, body.service_key, user.user_id)

# ---------- admin ----------

@router.post("/admin/services", status_code=201)
async def create_service(body: CreateServiceRequest, _: CurrentUser = Depends(require_roles("admin")),
                         uc=Depends(get_create_service_uc)) -> dict:
    return await uc.execute(body.model_dump())


@router.patch("/admin/services/{service_id}")
async def update_service(service_id: str, body: dict = Body(...), _: CurrentUser = Depends(require_roles("admin")),
                         uc=Depends(get_update_service_uc)) -> dict:
    return await uc.execute(service_id, body)


@router.delete("/admin/services/{service_id}")
async def deactivate_service(service_id: str, _: CurrentUser = Depends(require_roles("admin")),
                             uc=Depends(get_deactivate_service_uc)) -> dict:
    return await uc.execute(service_id)


@router.post("/admin/plans", status_code=201)
async def create_plan(body: CreatePlanRequest, _: CurrentUser = Depends(require_roles("admin")),
                      uc=Depends(get_create_plan_uc)) -> dict:
    return await uc.execute(body.model_dump())


@router.patch("/admin/plans/{plan_id}")
async def update_plan(plan_id: str, body: dict = Body(...), _: CurrentUser = Depends(require_roles("admin")),
                      uc=Depends(get_update_plan_uc)) -> dict:
    return await uc.execute(plan_id, body)


@router.get("/admin/companies")
async def list_companies(_: CurrentUser = Depends(require_roles("admin")), ucs=Depends(get_companies_ucs)) -> list[dict]:
    return await ucs[0].execute()


@router.post("/admin/companies", status_code=201)
async def create_company(body: CreateCompanyRequest, _: CurrentUser = Depends(require_roles("admin")),
                         ucs=Depends(get_companies_ucs)) -> dict:
    return await ucs[1].execute(body.model_dump())


@router.patch("/admin/companies/{company_id}")
async def update_company(company_id: str, body: dict = Body(...), _: CurrentUser = Depends(require_roles("admin")),
                         ucs=Depends(get_companies_ucs)) -> dict:
    return await ucs[2].execute(company_id, body)


@router.post("/admin/subscriptions", status_code=201)
async def create_subscription(body: CreateSubscriptionRequest, _: CurrentUser = Depends(require_roles("admin")),
                              uc=Depends(get_create_subscription_uc)) -> dict:
    return await uc.execute(body.model_dump(exclude_none=True))


@router.get("/admin/subscriptions")
async def list_subscriptions(_: CurrentUser = Depends(require_roles("admin")), repo=Depends(get_subs_repo)) -> list[dict]:
    return await repo.list_all()


@router.patch("/admin/subscriptions/{subscription_id}/status")
async def change_sub_status(subscription_id: str, body: dict = Body(...),
                            _: CurrentUser = Depends(require_roles("admin")),
                            uc=Depends(get_change_sub_status_uc)) -> dict:
    return await uc.execute(subscription_id, body["status"])


@router.patch("/admin/subscriptions/{subscription_id}/plan")
async def change_sub_plan(subscription_id: str, body: dict = Body(...),
                          _: CurrentUser = Depends(require_roles("admin")),
                          uc=Depends(get_change_sub_plan_uc)) -> dict:
    return await uc.execute(subscription_id, body["plan_id"])


@router.put("/admin/stores/{store_id}/services")
async def toggle_store_service(store_id: str, body: ToggleStoreServiceRequest,
                               _: CurrentUser = Depends(require_roles("admin")),
                               uc=Depends(get_toggle_store_service_uc)) -> dict:
    await uc.execute(store_id, body.service_key, body.enabled)
    return {"ok": True}


@router.get("/admin/interests")
async def list_interests(status: str | None = Query(None), _: CurrentUser = Depends(require_roles("admin")),
                         repo=Depends(get_interests_repo)) -> list[dict]:
    return await repo.list_by_status(status)


@router.patch("/admin/interests/{interest_id}")
async def update_interest(interest_id: str, body: dict = Body(...), _: CurrentUser = Depends(require_roles("admin")),
                          repo=Depends(get_interests_repo)) -> dict:
    return await repo.update(interest_id, body)
```
Em `src/main.py`, inclua `from src.modules.ecosystem.interface.router import router as ecosystem_router` e `app.include_router(ecosystem_router)`.

> Vincular loja a empresa: já funciona via `PATCH /admin/stores/{id}` existente com `{"company_id": "..."}` (o `UpdateStoreUseCase` aceita dict). Adicione `company_id` ao `StoreModel` (nota da Task 3).

- [ ] **Step 4: e2e (fluxo completo: serviço → plano → empresa → assinatura → toggle → entitlements)**

`tests/e2e/test_ecosystem.py`:
```python
import uuid
import pytest


async def _admin(client):
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_full_ecosystem_flow(client) -> None:
    h = await _admin(client)
    suffix = uuid.uuid4().hex[:6]

    svc = (await client.post("/admin/services", json={
        "key": f"crm_completo_{suffix}", "name": "CRM Completo", "type": "software",
        "feature_keys": ["crm.kanban", "agenda"]}, headers=h)).json()
    plan = (await client.post("/admin/plans", json={
        "key": f"pro_{suffix}", "name": "Pro", "service_keys": [svc["key"]]}, headers=h)).json()
    company = (await client.post("/admin/companies", json={"name": f"Grupo {suffix}"}, headers=h)).json()
    store = (await client.post("/admin/stores", json={"nome_fantasia": f"Loja {suffix}"}, headers=h)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"company_id": company["id"]}, headers=h)

    sub = await client.post("/admin/subscriptions", json={
        "company_id": company["id"], "plan_id": plan["id"], "status": "active"}, headers=h)
    assert sub.status_code == 201

    # antes de ligar o serviço na loja: nada desbloqueado
    ent = (await client.get(f"/ecosystem/my-entitlements?store_id={store['id']}", headers=h)).json()
    assert ent["feature_keys"] == []

    # liga o serviço na loja → keys aparecem
    await client.put(f"/admin/stores/{store['id']}/services",
                     json={"service_key": svc["key"], "enabled": True}, headers=h)
    ent = (await client.get(f"/ecosystem/my-entitlements?store_id={store['id']}", headers=h)).json()
    assert set(ent["feature_keys"]) == {"agenda", "crm.kanban"}

    # interesse (upsell) registrado
    res = await client.post("/ecosystem/interests",
                            json={"store_id": store["id"], "service_key": svc["key"]}, headers=h)
    assert res.status_code == 201
```
```bash
uv run pytest tests/e2e/test_ecosystem.py && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(ecosystem): admin routers, catalog and interests"
```

---

## Task 8: Aplicar os gates nos módulos existentes

**Files:** Modify os routers dos módulos (1 linha por rota gateada) + response-shaping no relatório.

- [ ] **Step 1: Gate por rota (mapa exato)**

Adicione `Depends(require_feature("<key>"))` (import `from src.shared.interface.feature_gate import require_feature`) nas rotas abaixo — todas já têm `store_id` como query param:

| Router | Rota | Key |
|---|---|---|
| `agenda` | `GET /agenda` | `agenda` |
| `metrics` | `GET /metrics/dashboard` | `metrics.dashboard` |
| `metrics` | `GET /metrics/reports` | `metrics.reports` |
| `metrics` | `GET /metrics/projections` | `metrics.projections` |
| `metrics` | `GET /metrics/team` | `metrics.team` |
| `marketing` | `GET /marketing/funnel`, `GET /marketing/by-campaign` | `metrics.marketing` |
| `marketing` | `GET/POST/PATCH /campaigns` | `marketing.campaigns` |
| `crm` | `GET /crm/funnels`, `GET /crm/leads` | `crm.kanban` |
| `indicators` | `GET/POST /indicators` | `indicators` |
| `goals` | `GET /goals` | `goals` |
| `action_plans` | `GET /action-plans` | `action_plans` |

Exemplo (agenda):
```python
@router.get("", dependencies=[Depends(require_feature("agenda"))])
```
> Rotas de escrita do CRM (`PATCH /crm/leads/{id}` etc.) não têm `store_id` na query — o Kanban inteiro já fica invisível sem `crm.kanban` na listagem; não gateie as rotas de item na v1 (nota técnica). `bulk_send` é admin-only (E7, sem gate). O webhook Z-API segue gateado pelas flags da loja (comportamento atual).

- [ ] **Step 2: Response-shaping da coluna de custos (E4)**

Na rota `GET /metrics/reports` (`src/modules/metrics/interface/router.py`), após obter o resultado, omita os custos sem a key:
```python
from src.modules.ecosystem.infrastructure.entitlement_service import EntitlementService
# dentro da rota reports, antes do return:
    result = await uc.execute(await _resolve(user, store_id, access), start, end, campaign_id)
    if user.role != "admin" and store_id:
        keys = await EntitlementService(session).feature_keys_for_store(store_id)
        if "metrics.reports.costs" not in keys:
            result["costs"] = None
            result["investment"] = None
    return result
```
> Injete `session: AsyncSession = Depends(get_session)` na assinatura da rota para isso.

- [ ] **Step 3: Rodar TUDO (os e2e antigos continuam verdes — E6: lojas sem empresa não são gateadas) + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(ecosystem): apply feature gates to modules"
```

---

## Task 9: Integração de cobrança (framework do dono) — desenvolvida e DESLIGADA

**Files:**
- Create: `src/modules/ecosystem/application/billing_events.py`
- Modify: `src/modules/ecosystem/interface/{deps.py,router.py}`
- Create: `docs/BILLING_GATEWAY.md` (no repo dos docs)
- Test: `tests/unit/ecosystem/test_billing_events.py`

- [ ] **Step 1: Teste (transições de status)**

`tests/unit/ecosystem/test_billing_events.py`:
```python
import pytest
from src.modules.ecosystem.application.billing_events import HandleBillingEventUseCase


class FakeSubs:
    def __init__(self, mode="gateway"): self.mode = mode; self.status_set = None
    async def get_or_raise(self, sid): return {"id": sid, "status": "active", "billing_mode": self.mode}
    async def update(self, sid, data): self.status_set = data.get("status"); return {"id": sid, **data}


class FakePayments:
    def __init__(self): self.saved = None
    async def create(self, data): self.saved = data; return {"id": "pay1", **data}


@pytest.mark.asyncio
async def test_confirmed_activates() -> None:
    subs, pays = FakeSubs(), FakePayments()
    uc = HandleBillingEventUseCase(subs, pays)
    await uc.execute({"subscription_id": "s1", "event_type": "payment_confirmed", "amount": 500})
    assert pays.saved["event_type"] == "payment_confirmed"
    assert subs.status_set == "active"


@pytest.mark.asyncio
async def test_overdue_suspends() -> None:
    subs = FakeSubs()
    uc = HandleBillingEventUseCase(subs, FakePayments())
    await uc.execute({"subscription_id": "s1", "event_type": "payment_overdue"})
    assert subs.status_set == "suspended"


@pytest.mark.asyncio
async def test_manual_mode_only_records() -> None:
    subs = FakeSubs(mode="manual")
    uc = HandleBillingEventUseCase(subs, FakePayments())
    await uc.execute({"subscription_id": "s1", "event_type": "payment_confirmed"})
    assert subs.status_set is None          # registra o pagamento mas não mexe no status
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/ecosystem/application/billing_events.py`:
```python
from src.shared.domain.errors import DomainError

_STATUS_BY_EVENT = {"payment_confirmed": "active", "payment_failed": "suspended",
                    "payment_overdue": "suspended", "payment_refunded": None}
_PAYMENT_STATUS = {"payment_confirmed": "confirmed", "payment_failed": "failed",
                   "payment_overdue": "overdue", "payment_refunded": "refunded"}


class HandleBillingEventUseCase:
    """Recebe eventos do framework de pagamentos do dono (E1): persiste sempre;
    transiciona o status só quando billing_mode = gateway."""

    def __init__(self, subscriptions, payments) -> None:
        self._subs = subscriptions
        self._payments = payments

    async def execute(self, event: dict) -> dict:
        event_type = event.get("event_type")
        if event_type not in _STATUS_BY_EVENT:
            raise DomainError(f"event_type desconhecido: {event_type}")
        sub = await self._subs.get_or_raise(event["subscription_id"])
        payment = await self._payments.create({
            "subscription_id": sub["id"], "external_id": event.get("external_id"),
            "gateway": event.get("gateway"), "event_type": event_type,
            "status": _PAYMENT_STATUS[event_type], "amount": event.get("amount"),
            "payload": event.get("raw") or {},
        })
        new_status = _STATUS_BY_EVENT[event_type]
        if new_status and sub.get("billing_mode") == "gateway":
            await self._subs.update(sub["id"], {"status": new_status})
        return payment
```

- [ ] **Step 3: Endpoint desligado por flag + token**

Em `src/modules/ecosystem/interface/deps.py`, adicione:
```python
from fastapi import Header, HTTPException
from src.modules.ecosystem.application.billing_events import HandleBillingEventUseCase
from src.modules.ecosystem.infrastructure.repositories import SubscriptionPaymentRepository


def require_billing_integration(x_billing_token: str = Header(...)) -> None:
    s = get_settings()
    if not s.billing_gateway_enabled:
        raise HTTPException(status_code=409, detail="Integração de cobrança desativada (BILLING_GATEWAY_ENABLED=false).")
    if x_billing_token != s.billing_token:
        raise HTTPException(status_code=401, detail="token inválido")


def get_billing_event_uc(s: AsyncSession = Depends(get_session)) -> HandleBillingEventUseCase:
    return HandleBillingEventUseCase(SubscriptionRepository(s), SubscriptionPaymentRepository(s))
```
Em `router.py`:
```python
from src.modules.ecosystem.interface.deps import get_billing_event_uc, require_billing_integration


@router.post("/integrations/billing/events", status_code=201, dependencies=[Depends(require_billing_integration)])
async def billing_event(body: dict = Body(...), uc=Depends(get_billing_event_uc)) -> dict:
    return await uc.execute(body)
```

- [ ] **Step 4: Escrever `docs/BILLING_GATEWAY.md`**

Crie o documento (no diretório `docs/` do repo de documentação) com este conteúdo:
```markdown
# Integração de Cobrança — Framework de Pagamentos ↔ Trivus Backend

## Estado atual
DESENVOLVIDA e DESLIGADA (`BILLING_GATEWAY_ENABLED=false`). A cobrança é manual:
o admin cria/ativa/suspende assinaturas; trials expiram sozinhos.

## Arquitetura
O backend NÃO integra gateways diretamente. O framework de pagamentos da Trivus
(que já integra vários gateways) é quem cobra — e reporta cada evento para:

POST /integrations/billing/events
Header: x-billing-token: <BILLING_TOKEN>

## Contrato do evento (o framework adapta qualquer gateway p/ este formato)
{
  "subscription_id": "<uuid da assinatura no Trivus Backend>",
  "event_type": "payment_confirmed | payment_failed | payment_overdue | payment_refunded",
  "external_id": "<id do pagamento no framework/gateway>",
  "gateway": "<nome do gateway que processou>",
  "amount": 500.00,
  "paid_at": "2026-07-10T12:00:00Z",
  "raw": { ...payload original do gateway (auditoria)... }
}

## O que o backend faz com cada evento
1. SEMPRE persiste em `subscription_payments` (histórico + payload bruto).
2. Se a assinatura tem `billing_mode = "gateway"`:
   - payment_confirmed → status "active"
   - payment_failed / payment_overdue → status "suspended"
   - payment_refunded → só registra (decisão manual)
   Assinaturas `billing_mode = "manual"` nunca têm o status alterado por eventos.

## Passo a passo para ATIVAR
1. Gere um token forte: `openssl rand -hex 32` → env `BILLING_TOKEN` (Railway + framework).
2. Configure o framework para POSTar os eventos na URL de produção com o header.
3. Mapeie os IDs: ao criar a cobrança no framework, guarde o `subscription_id` do
   Trivus; opcionalmente preencha `gateway_customer_id`/`gateway_subscription_id`
   via `PATCH /admin/subscriptions/...` (campos já existem).
4. Mude as assinaturas desejadas para `billing_mode = "gateway"`.
5. Ligue `BILLING_GATEWAY_ENABLED=true` e faça um teste de sandbox:
   evento `payment_confirmed` → assinatura ativa; `payment_overdue` → suspensa
   (usuários da empresa perdem acesso na hora — os gates leem o status na leitura).

## Rollback
Desligue `BILLING_GATEWAY_ENABLED` (eventos passam a responder 409) e volte
`billing_mode = "manual"` nas assinaturas afetadas.
```

- [ ] **Step 5: Rodar tudo + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(ecosystem): billing events integration (disabled by flag)"
```

---

## Task 10: Verificação final + concluir

- [ ] **Step 1: Suíte completa + smoke manual**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
```
Smoke local: criar serviço → plano → empresa → loja vinculada → assinatura trialing com `trial_ends_at` de ontem → `GET /ecosystem/my-entitlements` deve vir **vazio** (trial expirado); mudar pra `active` → keys aparecem.

- [ ] **Step 2: Commit + status**

```bash
git add -A && git commit -m "feat(ecosystem): complete ecosystem module"
```
Atualize o status do Plano 12 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Cobertura da spec (checklist)

| Item (`ECOSSISTEMA_TRIVUS.md`) | Onde |
|---|---|
| 4 conceitos separados (company/store/subscription/entitlements) | Tasks 3, 5, 6 |
| Catálogo de serviços com CRUD + guarda-corpos | Task 4 |
| Feature keys no código + picklist (`GET /ecosystem/feature-keys`) | Tasks 1, 7 |
| Grão livre (tela/card/área) — 403 + response-shaping | Tasks 6, 8 |
| Híbrido: plano na empresa, toggle por loja (validado) | Task 5 |
| Trial automático sem cron | Tasks 2, 6 |
| Legado sem ruptura (E6 company NULL, crm_enabled) | Task 6 |
| Upsell: catálogo + interesses + n8n + fila admin | Task 7 |
| Cobrança: manual + integração com framework desligada + tabelas + doc | Task 9 |
| Admin bypass (E7) | Task 6 |

## Resultado

- A plataforma vira o hub do ecossistema da holding: empresas com assinaturas (SaaS ↔ consultoria migram trocando plano), serviços gerenciáveis pelo admin desbloqueando telas/cards específicos, upsell com esteira comercial, e a cobrança pronta pra plugar no framework de pagamentos existente.

**Próximo:** [`11-cleanup-cutover.md`](./11-cleanup-cutover.md) (o ETL ganha o passo de criar empresas/assinaturas dos clientes atuais).
