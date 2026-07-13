# Plano 03 — Auth & Sessão (vertical slice hexagonal — TEMPLATE)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–02.

**Goal:** Login com JWT e senha em **argon2** (aceitando o hash legado `hashed_<senha>` e re-hasheando no 1º login), `/auth/me`, `/auth/change-password`, e as dependências de autorização (`get_current_user`, `require_roles`, escopo de loja). Tudo nas **4 camadas hexagonais**, com teste em cada uma.

**Architecture:** Módulo `auth` com `domain` (entidade `User` + ports), `application` (use cases), `infrastructure` (repositório SQLAlchemy, hasher argon2, JWT) e `interface` (router FastAPI + schemas Pydantic + wiring). Domínio do sistema: spec §6.1, §6.2, §9.

**Tech Stack:** mesmo de 02.

> **Este é o template.** Os módulos 04–10 repetem exatamente esta estrutura de 4 camadas e 4 níveis de teste (domínio puro → use case com fakes → repositório com Postgres → endpoint e2e).

---

## Task 1: Domínio — entidade `User` + ports

**Files:**
- Create: `src/modules/auth/domain/entities.py`, `ports.py`
- Create: `src/modules/auth/__init__.py` e os `__init__.py` das subpastas
- Create: `tests/unit/auth/test_user_entity.py`

- [ ] **Step 1: Teste do domínio (puro)**

`tests/unit/auth/test_user_entity.py`:
```python
from src.modules.auth.domain.entities import User


def test_user_is_admin() -> None:
    admin = User(id="1", email="a@b.com", name="A", role="admin", parent_store_id=None, active=True, password_hash="h")
    client = User(id="2", email="c@b.com", name="C", role="client", parent_store_id=None, active=True, password_hash="h")
    assert admin.is_admin() is True
    assert client.is_admin() is False
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
uv run pytest tests/unit/auth/test_user_entity.py
```
Expected: FALHA.

- [ ] **Step 3: Entidade + ports**

`src/modules/auth/domain/entities.py`:
```python
from dataclasses import dataclass


@dataclass
class User:
    id: str
    email: str
    name: str | None
    role: str  # admin | client | shop_user
    parent_store_id: str | None
    active: bool
    password_hash: str | None

    def is_admin(self) -> bool:
        return self.role == "admin"
```
`src/modules/auth/domain/ports.py`:
```python
from abc import ABC, abstractmethod
from src.modules.auth.domain.entities import User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...
    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...
    @abstractmethod
    async def update_password(self, user_id: str, password_hash: str) -> None: ...


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...
    @abstractmethod
    def verify(self, password: str, hashed: str | None) -> bool: ...
    @abstractmethod
    def needs_rehash(self, hashed: str | None) -> bool: ...


class TokenService(ABC):
    @abstractmethod
    def issue(self, claims: dict[str, object]) -> str: ...
    @abstractmethod
    def verify(self, token: str) -> dict[str, object]: ...
```
Crie os `__init__.py` vazios em `src/modules/auth/`, `domain/`, `application/`, `infrastructure/`, `interface/` e `tests/unit/auth/`.

- [ ] **Step 4: Rodar e ver passar + commit**

```bash
uv run pytest tests/unit/auth && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(auth): add user domain entity and ports"
```

---

## Task 2: Adapter `Argon2PasswordHasher` (argon2 + legado)

**Files:**
- Create: `src/modules/auth/infrastructure/password_hasher.py`
- Create: `tests/unit/auth/test_password_hasher.py`

- [ ] **Step 1: Teste**

`tests/unit/auth/test_password_hasher.py`:
```python
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher

h = Argon2PasswordHasher()


def test_hash_and_verify() -> None:
    hashed = h.hash("s3nha")
    assert hashed.startswith("$argon2")
    assert h.verify("s3nha", hashed) is True
    assert h.verify("errada", hashed) is False


def test_legacy_hash_accepted() -> None:
    assert h.verify("minhasenha", "hashed_minhasenha") is True
    assert h.verify("x", "hashed_y") is False


def test_needs_rehash() -> None:
    assert h.needs_rehash("hashed_abc") is True
    assert h.needs_rehash(h.hash("x")) is False


def test_empty_hash() -> None:
    assert h.verify("x", None) is False
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/auth/infrastructure/password_hasher.py`:
```python
from argon2 import PasswordHasher as Argon2
from argon2.exceptions import VerifyMismatchError, VerificationError
from src.modules.auth.domain.ports import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._ph = Argon2()

    def hash(self, password: str) -> str:
        return self._ph.hash(password)

    def verify(self, password: str, hashed: str | None) -> bool:
        if not hashed:
            return False
        if hashed.startswith("$argon2"):
            try:
                return self._ph.verify(hashed, password)
            except (VerifyMismatchError, VerificationError):
                return False
        # Hash legado do sistema antigo (spec §6.1).
        return hashed == f"hashed_{password}" or hashed == password

    def needs_rehash(self, hashed: str | None) -> bool:
        return not hashed or not hashed.startswith("$argon2")
```
```bash
uv run pytest tests/unit/auth/test_password_hasher.py
git add -A && git commit -m "feat(auth): add argon2 password hasher with legacy support"
```
Expected: PASSA.

---

## Task 3: Adapter `JwtTokenService`

**Files:**
- Create: `src/modules/auth/infrastructure/token_service.py`
- Create: `tests/unit/auth/test_token_service.py`

- [ ] **Step 1: Teste**

`tests/unit/auth/test_token_service.py`:
```python
from src.modules.auth.infrastructure.token_service import JwtTokenService

svc = JwtTokenService(secret="test-secret", expires_minutes=60)


def test_issue_and_verify() -> None:
    token = svc.issue({"sub": "u1", "role": "admin"})
    claims = svc.verify(token)
    assert claims["sub"] == "u1"
    assert claims["role"] == "admin"
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/auth/infrastructure/token_service.py`:
```python
from datetime import datetime, timedelta, timezone
import jwt
from src.modules.auth.domain.ports import TokenService


class JwtTokenService(TokenService):
    def __init__(self, secret: str, expires_minutes: int) -> None:
        self._secret = secret
        self._expires_minutes = expires_minutes

    def issue(self, claims: dict[str, object]) -> str:
        payload = dict(claims)
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=self._expires_minutes)
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def verify(self, token: str) -> dict[str, object]:
        return jwt.decode(token, self._secret, algorithms=["HS256"])
```
```bash
uv run pytest tests/unit/auth/test_token_service.py
git add -A && git commit -m "feat(auth): add jwt token service"
```
Expected: PASSA.

---

## Task 4: Use case `LoginUseCase` (com fakes)

**Files:**
- Create: `src/modules/auth/application/dto.py`, `login.py`
- Create: `tests/unit/auth/test_login_use_case.py`

> Aqui mora a regra (spec §6.1). Testado com **repositório/serviços fake** que implementam os ports — sem banco, sem framework.

- [ ] **Step 1: Teste com fakes**

`tests/unit/auth/test_login_use_case.py`:
```python
import pytest
from src.modules.auth.application.dto import LoginCommand
from src.modules.auth.application.login import LoginUseCase
from src.modules.auth.domain.entities import User
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.shared.domain.errors import ForbiddenError, UnauthorizedError


class FakeUserRepo:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.updated_password: str | None = None

    async def get_by_email(self, email): return self.user
    async def get_by_id(self, user_id): return self.user
    async def update_password(self, user_id, password_hash): self.updated_password = password_hash


class FakeToken:
    def issue(self, claims): return "token-123"
    def verify(self, token): return {}


def make(user):
    return LoginUseCase(FakeUserRepo(user), Argon2PasswordHasher(), FakeToken()), 


@pytest.mark.asyncio
async def test_unknown_email() -> None:
    uc = LoginUseCase(FakeUserRepo(None), Argon2PasswordHasher(), FakeToken())
    with pytest.raises(UnauthorizedError):
        await uc.execute(LoginCommand(email="x@y.com", password="p"))


@pytest.mark.asyncio
async def test_inactive_user() -> None:
    user = User(id="1", email="a@b.com", name="A", role="admin", parent_store_id=None, active=False, password_hash="hashed_p")
    uc = LoginUseCase(FakeUserRepo(user), Argon2PasswordHasher(), FakeToken())
    with pytest.raises(ForbiddenError):
        await uc.execute(LoginCommand(email="a@b.com", password="p"))


@pytest.mark.asyncio
async def test_login_ok_and_rehash() -> None:
    user = User(id="1", email="a@b.com", name="A", role="admin", parent_store_id=None, active=True, password_hash="hashed_p")
    repo = FakeUserRepo(user)
    uc = LoginUseCase(repo, Argon2PasswordHasher(), FakeToken())
    result = await uc.execute(LoginCommand(email="a@b.com", password="p"))
    assert result.access_token == "token-123"
    assert result.user.id == "1"
    assert repo.updated_password is not None and repo.updated_password.startswith("$argon2")
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/auth/application/dto.py`:
```python
from dataclasses import dataclass
from src.modules.auth.domain.entities import User


@dataclass
class LoginCommand:
    email: str
    password: str


@dataclass
class AuthResult:
    access_token: str
    user: User
```
`src/modules/auth/application/login.py`:
```python
from src.modules.auth.application.dto import AuthResult, LoginCommand
from src.modules.auth.domain.ports import PasswordHasher, TokenService, UserRepository
from src.shared.domain.errors import ForbiddenError, UnauthorizedError


class LoginUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordHasher, tokens: TokenService) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, command: LoginCommand) -> AuthResult:
        user = await self._users.get_by_email(command.email.strip())
        if user is None:
            raise UnauthorizedError("Usuário ou senha inválidos")
        if not user.active:
            raise ForbiddenError("Acesso bloqueado. Seu usuário está inativo.")
        if not self._hasher.verify(command.password, user.password_hash):
            raise UnauthorizedError("Usuário ou senha inválidos")
        if self._hasher.needs_rehash(user.password_hash):
            await self._users.update_password(user.id, self._hasher.hash(command.password))
        token = self._tokens.issue({"sub": user.id, "role": user.role, "parent_store_id": user.parent_store_id})
        return AuthResult(access_token=token, user=user)
```
```bash
uv run pytest tests/unit/auth/test_login_use_case.py
git add -A && git commit -m "feat(auth): add login use case"
```
Expected: PASSA.

---

## Task 5: Repositório SQLAlchemy (integração com Postgres)

**Files:**
- Create: `src/modules/auth/infrastructure/orm.py`, `repository.py`
- Create: `tests/integration/conftest.py`, `tests/integration/test_user_repository.py`

> O repositório **não** faz commit — a UnitOfWork (a session) é commitada no boundary da requisição (Task 6) ou revertida nos testes.

- [ ] **Step 1: Modelo ORM (mapeia a tabela `users` do schema-alvo)**

`src/modules/auth/infrastructure/orm.py`:
```python
from sqlalchemy import Boolean, String
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
```
> Ajuste os nomes de coluna ao `MODELO_ALVO.md` (ex.: se lá `parent_store_id` virou outro nome). Tipos `uuid` podem usar `String` ou `sqlalchemy.dialects.postgresql.UUID`.

- [ ] **Step 2: Mapper + repositório**

`src/modules/auth/infrastructure/repository.py`:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.auth.domain.entities import User
from src.modules.auth.domain.ports import UserRepository
from src.modules.auth.infrastructure.orm import UserModel


def _to_domain(row: UserModel) -> User:
    return User(
        id=str(row.id), email=row.email, name=row.name, role=row.role,
        parent_store_id=str(row.parent_store_id) if row.parent_store_id else None,
        active=row.active, password_hash=row.password_hash,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        row = (await self._session.execute(select(UserModel).where(UserModel.email == email))).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_by_id(self, user_id: str) -> User | None:
        row = await self._session.get(UserModel, user_id)
        return _to_domain(row) if row else None

    async def update_password(self, user_id: str, password_hash: str) -> None:
        row = await self._session.get(UserModel, user_id)
        if row:
            row.password_hash = password_hash
            await self._session.flush()
```

- [ ] **Step 3: Fixture de integração (rollback por teste)**

`tests/integration/conftest.py`:
```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.shared.infrastructure.settings import get_settings


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(get_settings().database_url)
    conn = await engine.connect()
    trans = await conn.begin()
    maker = async_sessionmaker(bind=conn, expire_on_commit=False)
    s = maker()
    try:
        yield s
    finally:
        await s.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()
```

- [ ] **Step 4: Teste de integração**

`tests/integration/test_user_repository.py`:
```python
import uuid
import pytest
from src.modules.auth.infrastructure.orm import UserModel
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository


@pytest.mark.asyncio
async def test_get_by_email_and_update_password(session) -> None:
    uid = str(uuid.uuid4())
    session.add(UserModel(id=uid, email=f"{uid}@t.com", name="T", role="admin", active=True, password_hash="hashed_x"))
    await session.flush()

    repo = SqlAlchemyUserRepository(session)
    found = await repo.get_by_email(f"{uid}@t.com")
    assert found is not None and found.id == uid

    await repo.update_password(uid, "$argon2id$novo")
    reloaded = await repo.get_by_id(uid)
    assert reloaded is not None and reloaded.password_hash == "$argon2id$novo"
```
> Pré-condição: `docker compose up -d db` rodando e `alembic upgrade head` aplicado.

- [ ] **Step 5: Rodar e ver passar + commit**

```bash
uv run pytest tests/integration/test_user_repository.py
git add -A && git commit -m "feat(auth): add sqlalchemy user repository"
```
Expected: PASSA.

---

## Task 6: Interface — `POST /auth/login` (e2e) + handlers + seed

**Files:**
- Create: `src/modules/auth/interface/schemas.py`, `deps.py`, `router.py`
- Create: `src/shared/interface/error_handlers.py`
- Create: `scripts/seed_admin.py`
- Modify: `src/shared/infrastructure/database.py` (commit no boundary), `src/main.py`
- Create: `tests/e2e/conftest.py`, `tests/e2e/test_auth.py`

- [ ] **Step 1: `get_session` commitando no fim da requisição**

Em `src/shared/infrastructure/database.py`, troque `get_session` por:
```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 2: Error handlers (domínio → HTTP)**

`src/shared/interface/error_handlers.py`:
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.shared.domain.errors import ForbiddenError, NotFoundError, UnauthorizedError

_STATUS = {UnauthorizedError: 401, ForbiddenError: 403, NotFoundError: 404}


def register_error_handlers(app: FastAPI) -> None:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        status = _STATUS.get(type(exc), 400)
        return JSONResponse(status_code=status, content={"error": str(exc)})

    for exc_type in (UnauthorizedError, ForbiddenError, NotFoundError):
        app.add_exception_handler(exc_type, handler)
```

- [ ] **Step 3: Schemas + wiring (deps) + router**

`src/modules/auth/interface/schemas.py`:
```python
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    parent_store_id: str | None


class LoginResponse(BaseModel):
    access_token: str
    user: UserResponse
```
`src/modules/auth/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.auth.application.login import LoginUseCase
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.auth.infrastructure.token_service import JwtTokenService
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.settings import get_settings


def get_token_service() -> JwtTokenService:
    s = get_settings()
    return JwtTokenService(secret=s.jwt_secret, expires_minutes=s.jwt_expires_minutes)


def get_login_use_case(session: AsyncSession = Depends(get_session)) -> LoginUseCase:
    return LoginUseCase(SqlAlchemyUserRepository(session), Argon2PasswordHasher(), get_token_service())
```
`src/modules/auth/interface/router.py`:
```python
from fastapi import APIRouter, Depends
from src.modules.auth.application.dto import LoginCommand
from src.modules.auth.application.login import LoginUseCase
from src.modules.auth.interface.deps import get_login_use_case
from src.modules.auth.interface.schemas import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, uc: LoginUseCase = Depends(get_login_use_case)) -> LoginResponse:
    result = await uc.execute(LoginCommand(email=str(body.email), password=body.password))
    u = result.user
    return LoginResponse(
        access_token=result.access_token,
        user=UserResponse(id=u.id, email=u.email, name=u.name, role=u.role, parent_store_id=u.parent_store_id),
    )
```

- [ ] **Step 4: Registrar router + handlers no `main.py`**

Em `src/main.py`: importe `register_error_handlers` e o `router as auth_router`, chame `register_error_handlers(app)` e `app.include_router(auth_router)` dentro de `create_app`.

- [ ] **Step 5: Seed do admin**

`scripts/seed_admin.py`:
```python
import asyncio
import uuid
from sqlalchemy import select
from src.modules.auth.infrastructure.orm import UserModel
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.shared.infrastructure.database import SessionFactory


async def main() -> None:
    email, password = "admin@trivus.local", "admin123"
    async with SessionFactory() as s:
        exists = (await s.execute(select(UserModel).where(UserModel.email == email))).scalar_one_or_none()
        if not exists:
            s.add(UserModel(id=str(uuid.uuid4()), email=email, name="Admin Trivus", role="admin",
                            active=True, password_hash=Argon2PasswordHasher().hash(password)))
            await s.commit()
    print(f"Seeded admin: {email}")


if __name__ == "__main__":
    asyncio.run(main())
```
Rode: `uv run python -m scripts.seed_admin`.

- [ ] **Step 6: e2e**

`tests/e2e/conftest.py`:
```python
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```
`tests/e2e/test_auth.py`:
```python
import pytest


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client) -> None:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_ok(client) -> None:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "admin"
```
> Pré-condição: `docker compose up -d db`, `alembic upgrade head`, e `uv run python -m scripts.seed_admin`.

- [ ] **Step 7: Rodar tudo + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(auth): add login endpoint, error handlers and seed"
```
Expected: tudo verde.

---

## Task 7: `get_current_user` + `GET /auth/me`

**Files:**
- Create: `src/shared/interface/auth_deps.py`
- Modify: `src/modules/auth/interface/router.py`, `deps.py`
- Modify: `tests/e2e/test_auth.py`

- [ ] **Step 1: Dependência de usuário atual**

`src/shared/interface/auth_deps.py`:
```python
from dataclasses import dataclass
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.modules.auth.interface.deps import get_token_service
from src.modules.auth.infrastructure.token_service import JwtTokenService
from src.shared.domain.errors import UnauthorizedError

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user_id: str
    role: str
    parent_store_id: str | None


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    tokens: JwtTokenService = Depends(get_token_service),
) -> CurrentUser:
    if cred is None:
        raise UnauthorizedError("Token ausente")
    try:
        claims = tokens.verify(cred.credentials)
    except Exception as exc:
        raise UnauthorizedError("Token inválido") from exc
    return CurrentUser(user_id=str(claims["sub"]), role=str(claims["role"]), parent_store_id=claims.get("parent_store_id"))  # type: ignore[arg-type]
```

- [ ] **Step 2: `GetMeUseCase` + rota**

Crie `src/modules/auth/application/get_me.py` com `GetMeUseCase` (recebe `user_id`, usa `UserRepository.get_by_id`, levanta `NotFoundError` se não achar, retorna `User`). Adicione `get_me_use_case` em `deps.py` e a rota:
```python
from fastapi import Depends
from src.shared.interface.auth_deps import CurrentUser, get_current_user
# ...
@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser = Depends(get_current_user), uc: GetMeUseCase = Depends(get_me_use_case)) -> UserResponse:
    u = await uc.execute(user.user_id)
    return UserResponse(id=u.id, email=u.email, name=u.name, role=u.role, parent_store_id=u.parent_store_id)
```

- [ ] **Step 3: e2e + commit**

Adicione testes: `GET /auth/me` sem token → 401; com token do login → 200 e `email == admin@trivus.local`.
```bash
uv run pytest tests/e2e/test_auth.py
git add -A && git commit -m "feat(auth): add current-user dependency and /auth/me"
```

---

## Task 8: Autorização — `require_roles` e escopo de loja

**Files:**
- Create: `src/shared/interface/rbac.py`
- Create: `src/modules/auth/application/store_access.py` (+ teste)

- [ ] **Step 1: `require_roles` (factory de dependência)**

`src/shared/interface/rbac.py`:
```python
from collections.abc import Callable
from fastapi import Depends
from src.shared.domain.errors import ForbiddenError
from src.shared.interface.auth_deps import CurrentUser, get_current_user


def require_roles(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if roles and user.role not in roles:
            raise ForbiddenError("Acesso negado para o seu perfil.")
        return user
    return checker
```
Uso nos módulos: `user: CurrentUser = Depends(require_roles("admin"))`.

- [ ] **Step 2: Escopo de loja (port + use case) — spec §6.2**

Crie um port `StoreAccessReader` (domain) e um use case `GetAccessibleStoreIds(user_id, role, parent_store_id) -> list[str] | None` (`None` = admin/todas; `shop_user` → `[parent_store_id]`; `client` → ids de `user_store_access`). Teste com um fake do reader cobrindo os 3 papéis (igual ao padrão da Task 4). A implementação SQLAlchemy do reader entra no Plano 04 (Stores), mas o **port + use case** já ficam aqui para os módulos consumirem.

- [ ] **Step 3: Verificar + commit**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(auth): add rbac and store-scope use case"
```

---

## Task 9: `POST /auth/change-password` (e2e)

**Files:** `src/modules/auth/application/change_password.py`, schema, rota, teste.

- [ ] **Step 1: Use case**

`ChangePasswordUseCase(execute(user_id, current_password, new_password))`: busca user (`NotFoundError`), verifica `current_password` (`UnauthorizedError` se errado), grava `hasher.hash(new_password)` via `update_password`. Teste unit com fakes (igual Task 4).

- [ ] **Step 2: Schema + rota protegida**

`ChangePasswordRequest(current_password, new_password)`; rota `POST /auth/change-password` com `Depends(get_current_user)`.

- [ ] **Step 3: e2e (troca e re-loga; restaura no fim) + commit + concluir**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(auth): add change-password endpoint"
```
Atualize o status do Plano 03 para ✅ em [`00-INDEX.md`](./00-INDEX.md) e commit.

---

## Task 10: Redeploy + smoke test do login em prod

- [ ] **Step 1: Segredos na Railway**

Garanta `JWT_SECRET` forte em prod. Rode o seed: `railway run uv run python -m scripts.seed_admin`.

- [ ] **Step 2: Deploy + smoke test**

```bash
git push && railway up
curl -s -X POST https://<sua-url>/auth/login -H 'Content-Type: application/json' -d '{"email":"admin@trivus.local","password":"admin123"}'
```
Expected: JSON com `access_token` e `user.role = "admin"`.

---

## Resultado deste plano

- Login JWT + argon2 (com migração do hash legado), `/auth/me`, `/auth/change-password`, `require_roles` e escopo de loja — tudo nas 4 camadas hexagonais com teste em cada nível.
- **O template está estabelecido.** Cada módulo de 04–10 repete: domínio+ports → use case (fakes) → repositório (Postgres) → router (e2e).

**Próximo:** Plano 04 — Usuários & Lojas.
