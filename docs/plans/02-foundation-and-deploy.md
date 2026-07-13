# Plano 02 — Fundação & Deploy (FastAPI hexagonal, do zero ao prod)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua o [`01-data-discovery-modeling.md`](./01-data-discovery-modeling.md) (o `MODELO_ALVO.md` é usado na Task 5).

**Goal:** Projeto FastAPI com estrutura hexagonal, Postgres em Docker Compose, SQLAlchemy async + Alembic criando o **schema-alvo**, endpoint `/health` testado, CI (ruff+mypy+pytest) e **deploy em produção na Railway**.

**Architecture:** Hexagonal/DDD (ver `00-INDEX`). Para **testar** o pipeline, local e prod usam um Postgres **novo** criado pela migration do schema-alvo (a migração dos dados reais é o Plano 11).

**Tech Stack:** Python 3.12, uv, FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic, Pydantic v2, pytest, ruff, mypy, Docker, Railway.

> **Pré-requisitos:** Python 3.12, `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`), Docker Desktop, git, conta GitHub + Railway. Falta algo? Peça ao humano.

---

## Task 1: Scaffold do projeto com uv

**Files:** `trivus-backend/` (novo projeto)

- [ ] **Step 1: Criar o projeto**

A partir da pasta dos projetos (ex.: `~/Documents/cliick/trivus`):
```bash
uv init trivus-backend --python 3.12
cd trivus-backend
rm -f hello.py main.py   # remove o arquivo de exemplo, se houver
mkdir -p src/shared/domain src/shared/application src/shared/infrastructure src/shared/interface src/modules tests/unit tests/integration tests/e2e
```

- [ ] **Step 2: Adicionar dependências**

```bash
uv add "fastapi" "uvicorn[standard]" "sqlalchemy[asyncio]" asyncpg alembic "pydantic-settings" pyjwt argon2-cffi
uv add --dev pytest pytest-asyncio httpx ruff mypy testcontainers
```
Expected: dependências no `pyproject.toml`.

- [ ] **Step 3: Configurar pyproject (ruff, mypy, pytest)**

Acrescente ao `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
src = ["src"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 4: git init + commit**

```bash
git init
printf "%s\n" "__pycache__/" ".venv/" ".env" "*.pyc" > .gitignore
git add -A && git commit -m "chore: scaffold fastapi project with uv"
```

---

## Task 2: Configuração (settings) validada

**Files:**
- Create: `src/shared/infrastructure/settings.py`
- Create: `.env`, `.env.example`

- [ ] **Step 1: Criar `.env.example` e `.env`**

`.env.example`:
```env
ENV=development
DATABASE_URL=postgresql+asyncpg://trivus:trivus@localhost:5432/trivus
JWT_SECRET=dev-change-me
JWT_EXPIRES_MINUTES=10080
```
```bash
cp .env.example .env
```

- [ ] **Step 2: Settings com pydantic-settings**

`src/shared/infrastructure/settings.py`:
```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 10080


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 3: Verificar + commit**

```bash
uv run python -c "from src.shared.infrastructure.settings import get_settings; print(get_settings().env)"
git add -A && git commit -m "feat: add validated settings"
```
Expected: imprime `development`.

---

## Task 3: Postgres local via Docker Compose

**Files:** `docker-compose.yml`

- [ ] **Step 1: Criar `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: trivus-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: trivus
      POSTGRES_PASSWORD: trivus
      POSTGRES_DB: trivus
    ports:
      - '5432:5432'
    volumes:
      - trivus-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U trivus -d trivus']
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  trivus-db-data:
```

- [ ] **Step 2: Subir e confirmar saúde**

```bash
docker compose up -d db
docker compose ps
```
Expected: `db` com status `healthy`.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add local postgres via docker compose"
```

---

## Task 4: SQLAlchemy async + Alembic

**Files:**
- Create: `src/shared/infrastructure/database.py`
- Create: `migrations/` (Alembic async)
- Modify: `alembic.ini`, `migrations/env.py`

- [ ] **Step 1: Engine e session async**

`src/shared/infrastructure/database.py`:
```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from src.shared.infrastructure.settings import get_settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(get_settings().database_url, echo=False, future=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        yield session
```

- [ ] **Step 2: Inicializar Alembic (template async)**

```bash
uv run alembic init -t async migrations
```
Expected: cria `alembic.ini` e `migrations/`.

- [ ] **Step 3: Apontar o Alembic para o settings**

Em `migrations/env.py`, substitua a leitura da URL por:
```python
from src.shared.infrastructure.settings import get_settings
from src.shared.infrastructure.database import Base
# ... dentro do arquivo:
config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata
```
(Remova/ajuste a linha original que lê a URL do `alembic.ini`.)

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: add sqlalchemy async and alembic"
```

---

## Task 5: Migration inicial — criar o schema-alvo

**Files:** `migrations/versions/<rev>_initial_schema.py`

> Usa o DDL do `docs/db/MODELO_ALVO.md` (Plano 01). Abordagem **migration-first**: o schema é a fonte da verdade; os modelos SQLAlchemy de cada módulo (planos seguintes) mapeiam para estas tabelas.

- [ ] **Step 1: Criar a migration vazia**

```bash
uv run alembic revision -m "initial schema"
```
Expected: cria um arquivo em `migrations/versions/`.

- [ ] **Step 2: Preencher `upgrade()`/`downgrade()` com o schema-alvo**

No arquivo criado, em `upgrade()`, use `op.execute(""" ... """)` colando o **DDL-alvo** do `docs/db/MODELO_ALVO.md` (todas as tabelas, com FKs, CHECKs de enum, uniques e índices). Em `downgrade()`, `op.execute("DROP TABLE ... CASCADE")` na ordem inversa. Comece o `upgrade()` com `op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')` (para `gen_random_uuid()`).

> Se o `MODELO_ALVO.md` ainda tiver itens "decidir com o humano" (ex.: política `ON DELETE`), resolva-os com o humano **antes** de escrever a migration. Não invente.

- [ ] **Step 3: Aplicar no banco local**

```bash
uv run alembic upgrade head
docker compose exec db psql -U trivus -d trivus -c "\dt"
```
Expected: as tabelas do schema-alvo criadas.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: initial migration with clean target schema"
```

---

## Task 6: Bases hexagonais compartilhadas + `/health` (TDD)

**Files:**
- Create: `src/shared/domain/entity.py`, `src/shared/domain/errors.py`, `src/shared/application/use_case.py`
- Create: `src/modules/health/interface/router.py`
- Create: `src/main.py`
- Create: `tests/e2e/test_health.py`

- [ ] **Step 1: Bases do domínio/aplicação**

`src/shared/domain/errors.py`:
```python
class DomainError(Exception):
    """Erro de regra de negócio."""


class NotFoundError(DomainError):
    pass


class UnauthorizedError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass
```
`src/shared/application/use_case.py`:
```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

I = TypeVar("I")
O = TypeVar("O")


class UseCase(ABC, Generic[I, O]):
    @abstractmethod
    async def execute(self, request: I) -> O: ...
```
`src/shared/domain/entity.py`:
```python
from dataclasses import dataclass


@dataclass
class Entity:
    id: str
```

- [ ] **Step 2: Teste e2e que falha**

`tests/e2e/test_health.py`:
```python
import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
```

- [ ] **Step 3: Rodar e ver falhar**

```bash
uv run pytest tests/e2e/test_health.py
```
Expected: FALHA (sem `app`/rota).

- [ ] **Step 4: Router de health + app**

`src/modules/health/interface/router.py`:
```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```
`src/main.py`:
```python
from fastapi import FastAPI
from src.modules.health.interface.router import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Trivus Backend")
    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 5: Rodar e ver passar**

```bash
uv run pytest tests/e2e/test_health.py
uv run ruff check . && uv run mypy src
```
Expected: PASSA; lint e tipos OK.

- [ ] **Step 6: Subir manualmente**

```bash
uv run uvicorn src.main:app --reload --port 3001
# outro terminal:
curl -s http://localhost:3001/health
```
Expected: `{"status":"ok"}`. Pare com `Ctrl+C`.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: add hexagonal bases and health endpoint"
```

---

## Task 7: Dockerfile + serviço `api` no Compose

**Files:** `Dockerfile`, `.dockerignore`, `docker-compose.yml`

- [ ] **Step 1: `.dockerignore`**

```
.venv
__pycache__
.git
.env
```

- [ ] **Step 2: `Dockerfile` (com uv)**

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
EXPOSE 3001
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 3001"]
```

- [ ] **Step 3: Adicionar serviço `api` ao compose**

Dentro de `services:` (acima de `volumes:`):
```yaml
  api:
    build: .
    container_name: trivus-api
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      ENV: production
      DATABASE_URL: postgresql+asyncpg://trivus:trivus@db:5432/trivus
      JWT_SECRET: dev-change-me
    ports:
      - '3001:3001'
```

- [ ] **Step 4: Build, subir e testar**

```bash
docker compose up -d --build
sleep 6 && curl -s http://localhost:3001/health
docker compose down
```
Expected: `{"status":"ok"}`.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: containerize api"
```

---

## Task 8: CI (GitHub Actions)

**Files:** `.github/workflows/ci.yml`

- [ ] **Step 1: Workflow**

```yaml
name: CI
on:
  push:
    branches: ['**']
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_USER: trivus, POSTGRES_PASSWORD: trivus, POSTGRES_DB: trivus }
        ports: ['5432:5432']
        options: >-
          --health-cmd "pg_isready -U trivus -d trivus" --health-interval 5s --health-timeout 5s --health-retries 5
    env:
      DATABASE_URL: postgresql+asyncpg://trivus:trivus@localhost:5432/trivus
      JWT_SECRET: ci-secret
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --frozen
      - run: uv run alembic upgrade head
      - run: uv run ruff check .
      - run: uv run mypy src
      - run: uv run pytest
```

- [ ] **Step 2: Repo no GitHub + push**

```bash
git add -A && git commit -m "ci: add github actions pipeline"
gh repo create trivus-backend --private --source=. --push
gh run watch
```
Expected: CI verde. (Sem `gh`? Crie o repo no site e `git remote add origin <url> && git push -u origin main`.)

---

## Task 9: Deploy em produção (Railway) + smoke test

> Postgres **novo** na Railway (dados reais = Plano 11).

- [ ] **Step 1: CLI + projeto**

```bash
npm i -g @railway/cli   # ou: brew install railway
railway login
railway init
```

- [ ] **Step 2: Provisionar Postgres**

`railway open` → New → Database → PostgreSQL. A Railway cria a `DATABASE_URL`.

- [ ] **Step 3: Variáveis do serviço da API**

No serviço da API → Variables: `DATABASE_URL` referenciando o Postgres do projeto **com o driver async** — use `${{Postgres.DATABASE_URL}}` e garanta o prefixo `postgresql+asyncpg://` (se a Railway fornecer `postgresql://`, adicione uma var `DATABASE_URL` reescrita para `postgresql+asyncpg://...`). Adicione `JWT_SECRET` (gere com `openssl rand -hex 32`) e `ENV=production`.

- [ ] **Step 4: Deploy**

```bash
railway up
```
Expected: build do Dockerfile; `alembic upgrade head` cria o schema-alvo no Postgres da Railway; app sobe.

- [ ] **Step 5: Domínio público + smoke test**

Settings → Networking → Generate Domain. Depois:
```bash
curl -s https://<sua-url>.up.railway.app/health
```
Expected: `{"status":"ok"}`.

- [ ] **Step 6: Concluir**

Atualize o status do Plano 02 para ✅ em [`00-INDEX.md`](./00-INDEX.md) e commit.

---

## Resultado

- FastAPI hexagonal rodando local e em prod; schema-alvo limpo criado via Alembic; `/health` testado; CI com ruff+mypy+pytest; deploy público.

**Próximo:** [`03-auth.md`](./03-auth.md) — a vertical slice hexagonal completa (template dos módulos).
