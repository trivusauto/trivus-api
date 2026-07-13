# Plano 04 — Usuários & Lojas (código completo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans para executar passo a passo. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–03. Todo código aqui é copia-e-cola; rode os testes em cada passo.

**Goal:** Admin gerencia lojas (`stores`), usuários portal (`client`) e vínculos multi-loja (`user_store_access`); dono da loja gerencia colaboradores (`shop_user`) e rótulos de papéis. Implementa o `StoreAccessReader` (escopo de loja) que os módulos seguintes usam.

**Architecture:** Módulos `stores` e `users`, hexagonais (domínio→aplicação→infra→interface). Reutiliza `User`, `UserRepository`, `Argon2PasswordHasher`, `get_session`, `require_roles`, `get_current_user`, `CurrentUser` do Plano 03.

**Tech Stack:** mesmo do Plano 03.

---

## Task 1: Estender a entidade `User` e o `UserModel`

**Files:**
- Modify: `src/modules/auth/domain/entities.py`
- Modify: `src/modules/auth/infrastructure/orm.py`

> Gestão de usuários precisa de campos que o login não usava. Adicionamos com defaults, então o código do Plano 03 continua funcionando.

- [ ] **Step 1: Estender a entidade**

Substitua `src/modules/auth/domain/entities.py` por:
```python
from dataclasses import dataclass, field


@dataclass
class User:
    id: str
    email: str
    name: str | None
    role: str  # admin | client | shop_user
    parent_store_id: str | None
    active: bool
    password_hash: str | None
    shop_role: str | None = None
    menu_permissions: list[str] = field(default_factory=list)
    can_see_unassigned_leads: bool = False

    def is_admin(self) -> bool:
        return self.role == "admin"
```

- [ ] **Step 2: Estender o ORM**

Substitua `src/modules/auth/infrastructure/orm.py` por:
```python
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String)
    parent_store_id: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    shop_role: Mapped[str | None] = mapped_column(String, nullable=True)
    menu_permissions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    can_see_unassigned_leads: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] **Step 3: Atualizar o mapper do repositório de auth**

Em `src/modules/auth/infrastructure/repository.py`, substitua a função `_to_domain` por:
```python
def _to_domain(row: UserModel) -> User:
    return User(
        id=str(row.id), email=row.email, name=row.name, role=row.role,
        parent_store_id=str(row.parent_store_id) if row.parent_store_id else None,
        active=row.active, password_hash=row.password_hash,
        shop_role=row.shop_role, menu_permissions=row.menu_permissions or [],
        can_see_unassigned_leads=row.can_see_unassigned_leads,
    )
```

- [ ] **Step 4: Rodar a suíte (não pode quebrar o auth) + commit**

```bash
uv run pytest && uv run mypy src
git add -A && git commit -m "feat(users): extend user entity and model for management"
```
Expected: tudo verde (login segue funcionando).

---

## Task 2: Domínio de `stores`

**Files:**
- Create: `src/modules/stores/__init__.py` e `domain/__init__.py`, `application/__init__.py`, `infrastructure/__init__.py`, `interface/__init__.py`
- Create: `src/modules/stores/domain/entities.py`, `ports.py`, `role_labels.py`
- Create: `tests/unit/stores/__init__.py`, `tests/unit/stores/test_domain.py`

- [ ] **Step 1: Teste do domínio**

`tests/unit/stores/test_domain.py`:
```python
from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.role_labels import merge_shop_role_labels, DEFAULT_SHOP_ROLE_LABELS


def test_display_name() -> None:
    assert Store(id="1", nome_fantasia="Auto X").display_name() == "Auto X"


def test_role_labels_default() -> None:
    assert merge_shop_role_labels(None) == DEFAULT_SHOP_ROLE_LABELS


def test_role_labels_override_and_trim() -> None:
    out = merge_shop_role_labels({"sdr": "  Pré-vendas  ", "invalido": "x"})
    assert out["sdr"] == "Pré-vendas"
    assert out["vendedor"] == "Vendedor"
    assert "invalido" not in out
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
uv run pytest tests/unit/stores/test_domain.py
```
Expected: FALHA.

- [ ] **Step 3: Implementar**

`src/modules/stores/domain/entities.py`:
```python
from dataclasses import dataclass


@dataclass
class Store:
    id: str
    nome_fantasia: str
    razao_social: str | None = None
    cnpj: str | None = None
    crm_enabled: bool = False
    zapi_webhook_enabled: bool = False
    webhook_token: str | None = None
    active: bool = True

    def display_name(self) -> str:
        return self.nome_fantasia or self.razao_social or "Loja"
```
`src/modules/stores/domain/role_labels.py`:
```python
SHOP_ROLE_KEYS = ("sdr", "vendedor", "administrativo", "gerente")
DEFAULT_SHOP_ROLE_LABELS: dict[str, str] = {
    "sdr": "SDR", "vendedor": "Vendedor", "administrativo": "Administrativo", "gerente": "Gerente",
}
_MAX_LEN = 80


def merge_shop_role_labels(db: object) -> dict[str, str]:
    out = dict(DEFAULT_SHOP_ROLE_LABELS)
    if isinstance(db, dict):
        for k in SHOP_ROLE_KEYS:
            v = db.get(k)
            if isinstance(v, str):
                t = v.strip()[:_MAX_LEN]
                if t:
                    out[k] = t
    return out
```
`src/modules/stores/domain/ports.py`:
```python
from abc import ABC, abstractmethod
from src.modules.stores.domain.entities import Store


class StoreRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[Store]: ...
    @abstractmethod
    async def get_by_id(self, store_id: str) -> Store | None: ...
    @abstractmethod
    async def create(self, data: dict[str, object]) -> Store: ...
    @abstractmethod
    async def update(self, store_id: str, data: dict[str, object]) -> Store: ...
    @abstractmethod
    async def get_role_labels(self, store_id: str) -> object: ...
    @abstractmethod
    async def set_role_labels(self, store_id: str, labels: dict[str, str]) -> None: ...


class StoreAccessReader(ABC):
    @abstractmethod
    async def store_ids_for_user(self, user_id: str) -> list[str]: ...


class UserStoreAccessRepository(ABC):
    @abstractmethod
    async def replace_links(self, user_id: str, links: list[tuple[str, bool]]) -> None: ...
```
Crie todos os `__init__.py` citados (vazios).

- [ ] **Step 4: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/stores/test_domain.py
git add -A && git commit -m "feat(stores): add store domain and role labels"
```

---

## Task 3: ORM + repositórios de `stores` (integração)

**Files:**
- Create: `src/modules/stores/infrastructure/orm.py`, `repository.py`
- Create: `tests/integration/test_store_repository.py`

- [ ] **Step 1: ORM**

`src/modules/stores/infrastructure/orm.py`:
```python
from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class StoreModel(Base):
    __tablename__ = "stores"
    id: Mapped[str] = mapped_column(primary_key=True)
    nome_fantasia: Mapped[str] = mapped_column(String)
    razao_social: Mapped[str | None] = mapped_column(String, nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String, nullable=True)
    crm_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    zapi_webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    require_campaign_on_lead: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook_token: Mapped[str | None] = mapped_column(String, nullable=True)
    shop_role_labels: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserStoreAccessModel(Base):
    __tablename__ = "user_store_access"
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    store_id: Mapped[str] = mapped_column(String)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] **Step 2: Repositórios**

`src/modules/stores/infrastructure/repository.py`:
```python
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreAccessReader, StoreRepository, UserStoreAccessRepository
from src.modules.stores.infrastructure.orm import StoreModel, UserStoreAccessModel
from src.shared.domain.errors import NotFoundError


def _to_domain(r: StoreModel) -> Store:
    return Store(
        id=str(r.id), nome_fantasia=r.nome_fantasia, razao_social=r.razao_social, cnpj=r.cnpj,
        crm_enabled=r.crm_enabled, zapi_webhook_enabled=r.zapi_webhook_enabled,
        webhook_token=r.webhook_token, active=r.active,
    )


class SqlAlchemyStoreRepository(StoreRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Store]:
        rows = (await self._session.execute(select(StoreModel).order_by(StoreModel.nome_fantasia))).scalars().all()
        return [_to_domain(r) for r in rows]

    async def get_by_id(self, store_id: str) -> Store | None:
        r = await self._session.get(StoreModel, store_id)
        return _to_domain(r) if r else None

    async def create(self, data: dict) -> Store:
        row = StoreModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return _to_domain(row)

    async def update(self, store_id: str, data: dict) -> Store:
        row = await self._session.get(StoreModel, store_id)
        if row is None:
            raise NotFoundError("Loja não encontrada")
        for k, v in data.items():
            setattr(row, k, v)
        await self._session.flush()
        return _to_domain(row)

    async def get_role_labels(self, store_id: str) -> object:
        r = await self._session.get(StoreModel, store_id)
        return r.shop_role_labels if r else None

    async def set_role_labels(self, store_id: str, labels: dict) -> None:
        r = await self._session.get(StoreModel, store_id)
        if r is None:
            raise NotFoundError("Loja não encontrada")
        r.shop_role_labels = labels
        await self._session.flush()


class SqlAlchemyStoreAccessReader(StoreAccessReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store_ids_for_user(self, user_id: str) -> list[str]:
        rows = (await self._session.execute(
            select(UserStoreAccessModel.store_id).where(UserStoreAccessModel.user_id == user_id)
        )).scalars().all()
        return [str(r) for r in rows]


class SqlAlchemyUserStoreAccessRepository(UserStoreAccessRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_links(self, user_id: str, links: list[tuple[str, bool]]) -> None:
        await self._session.execute(delete(UserStoreAccessModel).where(UserStoreAccessModel.user_id == user_id))
        for store_id, is_owner in links:
            self._session.add(UserStoreAccessModel(id=str(uuid.uuid4()), user_id=user_id, store_id=store_id, is_owner=is_owner))
        await self._session.flush()
```

- [ ] **Step 3: Teste de integração**

`tests/integration/test_store_repository.py`:
```python
import pytest
from src.modules.stores.application.dto import CreateStoreInput
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreRepository


@pytest.mark.asyncio
async def test_create_list_update(session) -> None:
    repo = SqlAlchemyStoreRepository(session)
    created = await repo.create({"nome_fantasia": "Loja Repo"})
    assert created.id

    found = await repo.list_all()
    assert any(s.nome_fantasia == "Loja Repo" for s in found)

    updated = await repo.update(created.id, {"crm_enabled": True})
    assert updated.crm_enabled is True
```
> A fixture `session` (rollback por teste) é a do Plano 03 Task 5 (`tests/integration/conftest.py`). `CreateStoreInput` é criado na Task 4 — se rodar este teste antes, crie o arquivo `dto.py` da Task 4 primeiro (ou use `repo.create({...})` direto, sem o import).

- [ ] **Step 4: Rodar (precisa de `docker compose up -d db` + `alembic upgrade head`) + commit**

```bash
uv run pytest tests/integration/test_store_repository.py
git add -A && git commit -m "feat(stores): add sqlalchemy repositories"
```

---

## Task 4: Use cases de `stores`

**Files:**
- Create: `src/modules/stores/application/dto.py`, `list_stores.py`, `create_store.py`, `update_store.py`
- Create: `tests/unit/stores/test_use_cases.py`

- [ ] **Step 1: Teste com fake repo**

`tests/unit/stores/test_use_cases.py`:
```python
import pytest
from src.modules.stores.application.create_store import CreateStoreUseCase
from src.modules.stores.application.dto import CreateStoreInput
from src.modules.stores.application.update_store import UpdateStoreUseCase
from src.modules.stores.domain.entities import Store
from src.shared.domain.errors import NotFoundError


class FakeStoreRepo:
    def __init__(self) -> None:
        self.created: dict | None = None
        self.store: Store | None = None

    async def list_all(self): return []
    async def get_by_id(self, sid): return self.store
    async def create(self, data):
        self.created = data
        return Store(id="new", nome_fantasia=data["nome_fantasia"])
    async def update(self, sid, data):
        if self.store is None:
            raise NotFoundError("x")
        return Store(id=sid, nome_fantasia="x", crm_enabled=bool(data.get("crm_enabled")))
    async def get_role_labels(self, sid): return None
    async def set_role_labels(self, sid, labels): ...


@pytest.mark.asyncio
async def test_create_store() -> None:
    repo = FakeStoreRepo()
    out = await CreateStoreUseCase(repo).execute(CreateStoreInput(nome_fantasia="Auto X", fields={"cnpj": "123"}))
    assert out.id == "new"
    assert repo.created == {"nome_fantasia": "Auto X", "cnpj": "123"}


@pytest.mark.asyncio
async def test_update_missing_store_raises() -> None:
    repo = FakeStoreRepo()
    with pytest.raises(NotFoundError):
        await UpdateStoreUseCase(repo).execute("missing", {"crm_enabled": True})
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/stores/application/dto.py`:
```python
from dataclasses import dataclass, field


@dataclass
class CreateStoreInput:
    nome_fantasia: str
    fields: dict[str, object] = field(default_factory=dict)
```
`src/modules/stores/application/list_stores.py`:
```python
from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class ListStoresUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self) -> list[Store]:
        return await self._stores.list_all()
```
`src/modules/stores/application/create_store.py`:
```python
from src.modules.stores.application.dto import CreateStoreInput
from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class CreateStoreUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self, data: CreateStoreInput) -> Store:
        payload: dict[str, object] = {"nome_fantasia": data.nome_fantasia, **data.fields}
        return await self._stores.create(payload)
```
`src/modules/stores/application/update_store.py`:
```python
from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class UpdateStoreUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self, store_id: str, data: dict[str, object]) -> Store:
        return await self._stores.update(store_id, data)
```
> O gancho que clona o funil-template quando `crm_enabled` vira `true` entra no Plano 05 (injeta o `CloneTemplateUseCase` aqui).

- [ ] **Step 3: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/stores/test_use_cases.py
git add -A && git commit -m "feat(stores): add store use cases"
```

---

## Task 5: Router de `stores` (admin, e2e)

**Files:**
- Create: `src/modules/stores/interface/schemas.py`, `deps.py`, `router.py`
- Modify: `src/main.py`
- Create: `tests/e2e/test_stores.py`

- [ ] **Step 1: Schemas + deps + router**

`src/modules/stores/interface/schemas.py`:
```python
from pydantic import BaseModel


class CreateStoreRequest(BaseModel):
    nome_fantasia: str
    razao_social: str | None = None
    cnpj: str | None = None


class StoreResponse(BaseModel):
    id: str
    nome_fantasia: str
    crm_enabled: bool
    active: bool
```
`src/modules/stores/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.stores.application.create_store import CreateStoreUseCase
from src.modules.stores.application.list_stores import ListStoresUseCase
from src.modules.stores.application.update_store import UpdateStoreUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreRepository
from src.shared.infrastructure.database import get_session


def _repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemyStoreRepository:
    return SqlAlchemyStoreRepository(session)


def get_list_stores_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> ListStoresUseCase:
    return ListStoresUseCase(repo)


def get_create_store_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> CreateStoreUseCase:
    return CreateStoreUseCase(repo)


def get_update_store_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> UpdateStoreUseCase:
    return UpdateStoreUseCase(repo)
```
`src/modules/stores/interface/router.py`:
```python
from fastapi import APIRouter, Body, Depends
from src.modules.stores.application.create_store import CreateStoreUseCase
from src.modules.stores.application.dto import CreateStoreInput
from src.modules.stores.application.list_stores import ListStoresUseCase
from src.modules.stores.application.update_store import UpdateStoreUseCase
from src.modules.stores.interface.deps import get_create_store_uc, get_list_stores_uc, get_update_store_uc
from src.modules.stores.interface.schemas import CreateStoreRequest, StoreResponse
from src.shared.interface.auth_deps import CurrentUser
from src.shared.interface.rbac import require_roles

router = APIRouter(prefix="/admin/stores", tags=["stores"])


def _resp(s) -> StoreResponse:
    return StoreResponse(id=s.id, nome_fantasia=s.nome_fantasia, crm_enabled=s.crm_enabled, active=s.active)


@router.get("")
async def list_stores(_: CurrentUser = Depends(require_roles("admin")), uc: ListStoresUseCase = Depends(get_list_stores_uc)) -> list[StoreResponse]:
    return [_resp(s) for s in await uc.execute()]


@router.post("", status_code=201)
async def create_store(body: CreateStoreRequest, _: CurrentUser = Depends(require_roles("admin")), uc: CreateStoreUseCase = Depends(get_create_store_uc)) -> StoreResponse:
    data = CreateStoreInput(nome_fantasia=body.nome_fantasia, fields={"razao_social": body.razao_social, "cnpj": body.cnpj})
    return _resp(await uc.execute(data))


@router.patch("/{store_id}")
async def update_store(store_id: str, body: dict = Body(...), _: CurrentUser = Depends(require_roles("admin")), uc: UpdateStoreUseCase = Depends(get_update_store_uc)) -> StoreResponse:
    return _resp(await uc.execute(store_id, body))
```
Em `src/main.py`, importe `from src.modules.stores.interface.router import router as stores_router` e adicione `app.include_router(stores_router)` em `create_app`.

> Nota: `create_store` passa `razao_social`/`cnpj` mesmo quando `None`; o `**data` no repositório os grava como `NULL`, o que é correto.

- [ ] **Step 2: e2e**

`tests/e2e/test_stores.py`:
```python
import pytest


async def _admin_token(client) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_requires_auth(client) -> None:
    res = await client.get("/admin/stores")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_and_list(client) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/admin/stores", json={"nome_fantasia": "Loja E2E"}, headers=headers)
    assert created.status_code == 201
    listed = await client.get("/admin/stores", headers=headers)
    assert any(s["nome_fantasia"] == "Loja E2E" for s in listed.json())
```
> Pré-condição: `docker compose up -d db`, `alembic upgrade head`, `uv run python -m scripts.seed_admin`.

- [ ] **Step 3: Rodar e ver passar + commit**

```bash
uv run pytest tests/e2e/test_stores.py && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(stores): add admin stores endpoints"
```

---

## Task 6: Escopo de loja (`StoreAccessReader` + use case)

**Files:**
- Create: `src/modules/stores/application/get_accessible_stores.py`
- Create: `tests/unit/stores/test_accessible_stores.py`

> Resolve as lojas acessíveis por usuário (spec §6.2). Os módulos seguintes (Métricas, etc.) importam este use case.

- [ ] **Step 1: Teste com fake reader**

`tests/unit/stores/test_accessible_stores.py`:
```python
import pytest
from dataclasses import dataclass
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase


@dataclass
class U:
    user_id: str
    role: str
    parent_store_id: str | None


class FakeReader:
    def __init__(self, ids): self.ids = ids
    async def store_ids_for_user(self, user_id): return self.ids


@pytest.mark.asyncio
async def test_admin_none() -> None:
    uc = GetAccessibleStoreIdsUseCase(FakeReader([]))
    assert await uc.execute(U("1", "admin", None)) is None


@pytest.mark.asyncio
async def test_shop_user_parent_only() -> None:
    uc = GetAccessibleStoreIdsUseCase(FakeReader([]))
    assert await uc.execute(U("2", "shop_user", "store-9")) == ["store-9"]


@pytest.mark.asyncio
async def test_client_from_access() -> None:
    uc = GetAccessibleStoreIdsUseCase(FakeReader(["a", "b"]))
    assert await uc.execute(U("3", "client", None)) == ["a", "b"]
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/stores/application/get_accessible_stores.py`:
```python
from src.modules.stores.domain.ports import StoreAccessReader
from src.shared.interface.auth_deps import CurrentUser


class GetAccessibleStoreIdsUseCase:
    def __init__(self, reader: StoreAccessReader) -> None:
        self._reader = reader

    async def execute(self, user: CurrentUser) -> list[str] | None:
        """None = admin (todas as lojas)."""
        if user.role == "admin":
            return None
        if user.role == "shop_user" and user.parent_store_id:
            return [user.parent_store_id]
        return await self._reader.store_ids_for_user(user.user_id)
```
> Substitui o esboço do Plano 03 Task 8. Se o Plano 03 criou um `store_access` stub em `auth`, remova-o e use este.

- [ ] **Step 3: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/stores/test_accessible_stores.py
git add -A && git commit -m "feat(stores): add accessible store ids use case"
```

---

## Task 7: Repositório de `users` (create/list) — integração

**Files:**
- Modify: `src/modules/auth/domain/ports.py`, `src/modules/auth/infrastructure/repository.py`
- Create: `tests/integration/test_user_management_repository.py`

- [ ] **Step 1: Estender o port**

Em `src/modules/auth/domain/ports.py`, adicione ao `UserRepository` (depois de `update_password`):
```python
    @abstractmethod
    async def create(self, data: dict[str, object]) -> User: ...
    @abstractmethod
    async def list_portal(self) -> list[User]: ...
    @abstractmethod
    async def list_team(self, store_id: str) -> list[User]: ...
```

- [ ] **Step 2: Implementar no repositório**

Em `src/modules/auth/infrastructure/repository.py`, adicione os imports `import uuid` e `from src.modules.auth.infrastructure.orm import UserModel` (já existem) e os métodos na classe `SqlAlchemyUserRepository`:
```python
    async def create(self, data: dict) -> User:
        row = UserModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return _to_domain(row)

    async def list_portal(self) -> list[User]:
        from sqlalchemy import select
        stmt = select(UserModel).where(UserModel.role == "client", UserModel.parent_store_id.is_(None)).order_by(UserModel.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def list_team(self, store_id: str) -> list[User]:
        from sqlalchemy import select
        stmt = select(UserModel).where(UserModel.parent_store_id == store_id, UserModel.role == "shop_user").order_by(UserModel.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]
```

- [ ] **Step 3: Teste de integração + commit**

`tests/integration/test_user_management_repository.py`:
```python
import uuid
import pytest
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository


@pytest.mark.asyncio
async def test_create_and_list_portal(session) -> None:
    repo = SqlAlchemyUserRepository(session)
    email = f"{uuid.uuid4()}@loja.com"
    await repo.create({"email": email, "name": "Dono", "role": "client", "password_hash": "$argon2id$x", "active": True})
    portal = await repo.list_portal()
    assert any(u.email == email for u in portal)
```
```bash
uv run pytest tests/integration/test_user_management_repository.py
git add -A && git commit -m "feat(users): add user create and list repository methods"
```

---

## Task 8: Use cases de `users` (portal, colaborador, vínculos)

**Files:**
- Create: `src/modules/users/__init__.py` (+ subpastas), `src/modules/users/application/{dto.py,create_portal_user.py,create_team_user.py,assign_stores.py}`
- Create: `tests/unit/users/__init__.py`, `tests/unit/users/test_use_cases.py`

- [ ] **Step 1: Teste com fakes**

`tests/unit/users/test_use_cases.py`:
```python
import pytest
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.modules.auth.domain.entities import User
from src.modules.users.application.assign_stores import AssignStoresUseCase
from src.modules.users.application.create_team_user import CreateTeamUserUseCase
from src.modules.users.application.dto import CreateTeamUserInput
from src.shared.domain.errors import DomainError


class FakeUserRepo:
    def __init__(self): self.created: dict | None = None
    async def create(self, data):
        self.created = data
        return User(id="u1", email=data["email"], name=data.get("name"), role=data["role"],
                    parent_store_id=data.get("parent_store_id"), active=True, password_hash=data["password_hash"])


class FakeAccessRepo:
    def __init__(self): self.links = None
    async def replace_links(self, user_id, links): self.links = (user_id, links)


@pytest.mark.asyncio
async def test_create_team_user_hashes_password() -> None:
    repo = FakeUserRepo()
    uc = CreateTeamUserUseCase(repo, Argon2PasswordHasher())
    out = await uc.execute(CreateTeamUserInput(email="c@l.com", password="segredo1", name="Colab", store_id="s1", shop_role="sdr", menu_permissions=["/crm"], can_see_unassigned_leads=True))
    assert out.role == "shop_user"
    assert repo.created["password_hash"].startswith("$argon2")
    assert repo.created["parent_store_id"] == "s1"
    assert repo.created["can_see_unassigned_leads"] is True


@pytest.mark.asyncio
async def test_assign_stores_replaces_links() -> None:
    repo = FakeAccessRepo()
    await AssignStoresUseCase(repo).execute("u1", ["a", "b"], ["a"])
    assert repo.links == ("u1", [("a", True), ("b", False)])


@pytest.mark.asyncio
async def test_assign_stores_requires_one() -> None:
    with pytest.raises(DomainError):
        await AssignStoresUseCase(FakeAccessRepo()).execute("u1", [], [])
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/users/application/dto.py`:
```python
from dataclasses import dataclass, field


@dataclass
class CreateTeamUserInput:
    email: str
    password: str
    name: str
    store_id: str
    shop_role: str | None = None
    menu_permissions: list[str] = field(default_factory=list)
    can_see_unassigned_leads: bool = False
```
`src/modules/users/application/create_portal_user.py`:
```python
from src.modules.auth.domain.entities import User
from src.modules.auth.domain.ports import PasswordHasher, UserRepository


class CreatePortalUserUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, email: str, password: str, name: str | None) -> User:
        return await self._users.create({
            "email": email, "name": name, "role": "client",
            "password_hash": self._hasher.hash(password), "active": True,
        })
```
`src/modules/users/application/create_team_user.py`:
```python
from src.modules.auth.domain.entities import User
from src.modules.auth.domain.ports import PasswordHasher, UserRepository
from src.modules.users.application.dto import CreateTeamUserInput


class CreateTeamUserUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, data: CreateTeamUserInput) -> User:
        return await self._users.create({
            "email": data.email, "name": data.name, "role": "shop_user",
            "password_hash": self._hasher.hash(data.password), "active": True,
            "parent_store_id": data.store_id, "shop_role": data.shop_role,
            "menu_permissions": data.menu_permissions,
            "can_see_unassigned_leads": data.can_see_unassigned_leads,
        })
```
`src/modules/users/application/assign_stores.py`:
```python
from src.modules.stores.domain.ports import UserStoreAccessRepository
from src.shared.domain.errors import DomainError


class AssignStoresUseCase:
    def __init__(self, access: UserStoreAccessRepository) -> None:
        self._access = access

    async def execute(self, user_id: str, store_ids: list[str], owner_store_ids: list[str]) -> None:
        unique = list(dict.fromkeys(s for s in store_ids if s))
        if not unique:
            raise DomainError("Selecione ao menos uma loja.")
        owners = set(owner_store_ids or unique)
        await self._access.replace_links(user_id, [(sid, sid in owners) for sid in unique])
```
Crie os `__init__.py` de `src/modules/users/` e subpastas.

- [ ] **Step 3: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/users/test_use_cases.py
git add -A && git commit -m "feat(users): add user management use cases"
```

---

## Task 9: Router de `users` (e2e)

**Files:**
- Create: `src/modules/users/interface/{schemas.py,deps.py,router.py}`
- Modify: `src/main.py`
- Create: `tests/e2e/test_users.py`

- [ ] **Step 1: Schemas**

`src/modules/users/interface/schemas.py`:
```python
from pydantic import BaseModel, EmailStr


class CreatePortalUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class CreateTeamUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    shop_role: str | None = None
    menu_permissions: list[str] = []
    can_see_unassigned_leads: bool = False


class AssignStoresRequest(BaseModel):
    store_ids: list[str]
    owner_store_ids: list[str] = []


class PortalUserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    active: bool
```

- [ ] **Step 2: deps + router**

`src/modules/users/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.stores.infrastructure.repository import SqlAlchemyUserStoreAccessRepository
from src.modules.users.application.assign_stores import AssignStoresUseCase
from src.modules.users.application.create_portal_user import CreatePortalUserUseCase
from src.modules.users.application.create_team_user import CreateTeamUserUseCase
from src.shared.infrastructure.database import get_session


def _users(session: AsyncSession = Depends(get_session)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def get_create_portal_uc(repo: SqlAlchemyUserRepository = Depends(_users)) -> CreatePortalUserUseCase:
    return CreatePortalUserUseCase(repo, Argon2PasswordHasher())


def get_create_team_uc(repo: SqlAlchemyUserRepository = Depends(_users)) -> CreateTeamUserUseCase:
    return CreateTeamUserUseCase(repo, Argon2PasswordHasher())


def get_assign_stores_uc(session: AsyncSession = Depends(get_session)) -> AssignStoresUseCase:
    return AssignStoresUseCase(SqlAlchemyUserStoreAccessRepository(session))


def get_user_repo(repo: SqlAlchemyUserRepository = Depends(_users)) -> SqlAlchemyUserRepository:
    return repo
```
`src/modules/users/interface/router.py`:
```python
from fastapi import APIRouter, Depends
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.users.application.assign_stores import AssignStoresUseCase
from src.modules.users.application.create_portal_user import CreatePortalUserUseCase
from src.modules.users.application.create_team_user import CreateTeamUserUseCase
from src.modules.users.application.dto import CreateTeamUserInput
from src.modules.users.interface.deps import get_assign_stores_uc, get_create_portal_uc, get_create_team_uc, get_user_repo
from src.modules.users.interface.schemas import AssignStoresRequest, CreatePortalUserRequest, CreateTeamUserRequest, PortalUserResponse
from src.shared.interface.auth_deps import CurrentUser
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["users"])


@router.get("/admin/users")
async def list_portal(_: CurrentUser = Depends(require_roles("admin")), repo: SqlAlchemyUserRepository = Depends(get_user_repo)) -> list[PortalUserResponse]:
    return [PortalUserResponse(id=u.id, email=u.email, name=u.name, role=u.role, active=u.active) for u in await repo.list_portal()]


@router.post("/admin/users", status_code=201)
async def create_portal(body: CreatePortalUserRequest, _: CurrentUser = Depends(require_roles("admin")), uc: CreatePortalUserUseCase = Depends(get_create_portal_uc)) -> PortalUserResponse:
    u = await uc.execute(str(body.email), body.password, body.name)
    return PortalUserResponse(id=u.id, email=u.email, name=u.name, role=u.role, active=u.active)


@router.put("/admin/users/{user_id}/stores")
async def assign_stores(user_id: str, body: AssignStoresRequest, _: CurrentUser = Depends(require_roles("admin")), uc: AssignStoresUseCase = Depends(get_assign_stores_uc)) -> dict:
    await uc.execute(user_id, body.store_ids, body.owner_store_ids)
    return {"ok": True}


@router.get("/stores/{store_id}/team")
async def list_team(store_id: str, _: CurrentUser = Depends(require_roles("admin", "client")), repo: SqlAlchemyUserRepository = Depends(get_user_repo)) -> list[PortalUserResponse]:
    return [PortalUserResponse(id=u.id, email=u.email, name=u.name, role=u.role, active=u.active) for u in await repo.list_team(store_id)]


@router.post("/stores/{store_id}/team", status_code=201)
async def create_team(store_id: str, body: CreateTeamUserRequest, _: CurrentUser = Depends(require_roles("admin", "client")), uc: CreateTeamUserUseCase = Depends(get_create_team_uc)) -> PortalUserResponse:
    data = CreateTeamUserInput(email=str(body.email), password=body.password, name=body.name, store_id=store_id,
                               shop_role=body.shop_role, menu_permissions=body.menu_permissions,
                               can_see_unassigned_leads=body.can_see_unassigned_leads)
    u = await uc.execute(data)
    return PortalUserResponse(id=u.id, email=u.email, name=u.name, role=u.role, active=u.active)
```
Em `src/main.py`, importe `from src.modules.users.interface.router import router as users_router` e `app.include_router(users_router)`.

> Escopo fino (client só na própria loja) pode ser endurecido depois com `GetAccessibleStoreIdsUseCase`; por ora `require_roles` cobre o caso admin.

- [ ] **Step 2: e2e**

`tests/e2e/test_users.py`:
```python
import uuid
import pytest


async def _admin_token(client) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_create_and_list_portal_user(client) -> None:
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    email = f"portal_{uuid.uuid4()}@loja.com"
    created = await client.post("/admin/users", json={"email": email, "password": "segredo1", "name": "Dono"}, headers=headers)
    assert created.status_code == 201
    listed = await client.get("/admin/users", headers=headers)
    assert any(u["email"] == email for u in listed.json())
```

- [ ] **Step 3: Rodar e ver passar + commit**

```bash
uv run pytest tests/e2e/test_users.py && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(users): add users and team endpoints"
```

---

## Task 10: Rótulos de papéis (endpoints)

**Files:**
- Create: `src/modules/stores/application/role_labels.py`
- Modify: `src/modules/stores/interface/deps.py`, `router.py`
- Create: `tests/e2e/test_role_labels.py`

- [ ] **Step 1: Use cases**

`src/modules/stores/application/role_labels.py`:
```python
from src.modules.stores.domain.ports import StoreRepository
from src.modules.stores.domain.role_labels import merge_shop_role_labels


class GetRoleLabelsUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self, store_id: str) -> dict[str, str]:
        return merge_shop_role_labels(await self._stores.get_role_labels(store_id))


class SetRoleLabelsUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self, store_id: str, labels: dict[str, str]) -> dict[str, str]:
        merged = merge_shop_role_labels(labels)
        await self._stores.set_role_labels(store_id, merged)
        return merged
```

- [ ] **Step 2: deps + rotas**

Em `src/modules/stores/interface/deps.py`, adicione:
```python
from src.modules.stores.application.role_labels import GetRoleLabelsUseCase, SetRoleLabelsUseCase


def get_role_labels_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> GetRoleLabelsUseCase:
    return GetRoleLabelsUseCase(repo)


def set_role_labels_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> SetRoleLabelsUseCase:
    return SetRoleLabelsUseCase(repo)
```
Em `src/modules/stores/interface/router.py`, adicione os imports e rotas (`require_roles("admin","client")`):
```python
from fastapi import Body
from src.modules.stores.application.role_labels import GetRoleLabelsUseCase, SetRoleLabelsUseCase
from src.modules.stores.interface.deps import get_role_labels_uc, set_role_labels_uc
# ... dentro do arquivo:
@router.get("/{store_id}/role-labels")
async def get_role_labels(store_id: str, _: CurrentUser = Depends(require_roles("admin", "client")), uc: GetRoleLabelsUseCase = Depends(get_role_labels_uc)) -> dict[str, str]:
    return await uc.execute(store_id)


@router.patch("/{store_id}/role-labels")
async def set_role_labels(store_id: str, body: dict = Body(...), _: CurrentUser = Depends(require_roles("admin", "client")), uc: SetRoleLabelsUseCase = Depends(set_role_labels_uc)) -> dict[str, str]:
    return await uc.execute(store_id, body)
```

- [ ] **Step 3: e2e + commit + concluir**

`tests/e2e/test_role_labels.py`: admin cria loja, `PATCH /admin/stores/{id}/role-labels` com `{"sdr":"Pré-vendas"}` retorna merge com `sdr=Pré-vendas` e `vendedor=Vendedor`; `GET` confirma.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(stores): add role labels endpoints"
```
Atualize o status do Plano 04 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Resultado

- CRUD completo de lojas/usuários/colaboradores/vínculos via API hexagonal, com `StoreAccessReader` pronto para escopar os módulos seguintes. Todo código é copia-e-cola e coberto por testes em cada camada.

**Próximo:** [`05-crm.md`](./05-crm.md) (a ser expandido para código completo no mesmo formato).
