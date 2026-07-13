# Plano 07 — Agenda (código completo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–05. Código copia-e-cola.

**Goal:** `GET /agenda` — leads agendados com filtro de período por **tipo** (agendamento/comparecimento/fechamento), presets, busca, paginação e **escopo por papel**. Espelha `app/agenda/page.js`: retorna o lead completo, pagina com `total`, e a atribuição de `vendedor_id` reusa `PATCH /crm/leads/{id}` (Plano 05).

**Architecture:** Módulo `agenda`. `AgendaPeriod` é domínio puro. O reader SQLAlchemy retorna leads completos (`lead_to_dict` do Plano 05). Spec §6.7.

> **Espelho do front:** a tela lê `nome, telefone, cidade, agendado_por, vendedor_id, data_agendamento, hora_agendamento, compareceu_agendamento, fechou_negocio, observacoes, modelo/veiculo/ano` — por isso o endpoint devolve o lead inteiro (não uma projeção). Presets: `from_today, today, yesterday, previous_month, month, custom`. Página: 25/50/100.
>
> Crie os `__init__.py` de `src/modules/agenda/` e subpastas, e de `tests/unit/agenda/`.

---

## Task 1: Serviço de domínio `AgendaPeriod`

**Files:** `src/modules/agenda/domain/period.py` + `tests/unit/agenda/test_period.py`

- [ ] **Step 1: Teste**

`tests/unit/agenda/test_period.py`:
```python
from datetime import date
from src.modules.agenda.domain.period import AgendaPeriod

a = AgendaPeriod()
NOW = date(2026, 2, 15)


def test_date_field() -> None:
    assert a.date_field("agendamento") == "data_agendamento"
    assert a.date_field("comparecimento") == "data_compareceu"
    assert a.date_field("fechamento") == "data_fechou_negocio"


def test_ranges() -> None:
    assert a.resolve_range("today", now=NOW) == ("2026-02-15", "2026-02-15")
    assert a.resolve_range("month", now=NOW) == ("2026-02-01", "2026-02-28")
    assert a.resolve_range("from_today", now=NOW) == ("2026-02-15", None)


def test_custom_inverted() -> None:
    assert a.resolve_range("custom", "2026-02-20", "2026-02-10", now=NOW) == ("2026-02-10", "2026-02-20")
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/agenda/domain/period.py`:
```python
import calendar
from datetime import date, timedelta

_FIELD = {"agendamento": "data_agendamento", "comparecimento": "data_compareceu", "fechamento": "data_fechou_negocio"}


def _eom(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


class AgendaPeriod:
    def date_field(self, apply_to: str) -> str:
        return _FIELD.get(apply_to, _FIELD["agendamento"])

    def resolve_range(self, preset: str, custom_from: str = "", custom_to: str = "", now: date | None = None) -> tuple[str, str | None]:
        now = now or date.today()
        today = now.isoformat()
        if preset == "from_today":
            return today, None
        if preset == "today":
            return today, today
        if preset == "yesterday":
            y = (now - timedelta(days=1)).isoformat()
            return y, y
        if preset == "previous_month":
            first_prev = date(now.year, now.month, 1) - timedelta(days=1)
            return date(first_prev.year, first_prev.month, 1).isoformat(), _eom(first_prev).isoformat()
        if preset == "custom" and custom_from and custom_to:
            return (custom_to, custom_from) if custom_from > custom_to else (custom_from, custom_to)
        return date(now.year, now.month, 1).isoformat(), _eom(now).isoformat()
```
```bash
uv run pytest tests/unit/agenda/test_period.py
git add -A && git commit -m "feat(agenda): port agenda period"
```

---

## Task 2: Reader SQLAlchemy da agenda

**Files:** `src/modules/agenda/infrastructure/reader.py`

> Recebe **parâmetros de escopo** (não condições SQL) para manter a camada de aplicação limpa.

- [ ] **Step 1: Implementar**

`src/modules/agenda/infrastructure/reader.py`:
```python
from datetime import date
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.infrastructure.orm import LeadModel
from src.modules.crm.infrastructure.repositories import lead_to_dict


class AgendaReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query(self, *, store_id: str, apply_to: str, date_field: str, date_from: str, date_to: str | None,
                    scope: dict, search: str | None, page: int, page_size: int) -> tuple[list[dict], int]:
        stmt = select(LeadModel).where(LeadModel.store_id == store_id)

        if apply_to == "agendamento":
            stmt = stmt.where(LeadModel.data_agendamento.isnot(None), LeadModel.hora_agendamento.isnot(None))
        elif apply_to == "comparecimento":
            stmt = stmt.where(LeadModel.compareceu_agendamento.is_(True), LeadModel.data_compareceu.isnot(None))
        elif apply_to == "fechamento":
            stmt = stmt.where(LeadModel.fechou_negocio.is_(True), LeadModel.data_fechou_negocio.isnot(None))

        col = getattr(LeadModel, date_field)
        stmt = stmt.where(col >= date.fromisoformat(date_from))
        if date_to:
            stmt = stmt.where(col <= date.fromisoformat(date_to))

        if not scope.get("gestor"):
            uid = scope["user_id"]
            conds = [LeadModel.vendedor_id == uid, LeadModel.assigned_to == uid]
            if scope.get("include_unassigned"):
                conds.append(LeadModel.assigned_to.is_(None))
            stmt = stmt.where(or_(*conds))

        if search and search.strip():
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(LeadModel.nome.ilike(like), LeadModel.modelo.ilike(like), LeadModel.veiculo.ilike(like), LeadModel.telefone.ilike(like)))

        total = int((await self._session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one())
        stmt = stmt.order_by(col).limit(page_size).offset((page - 1) * page_size)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [lead_to_dict(r) for r in rows], total
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat(agenda): add agenda reader"
```

---

## Task 3: `ListAgendaUseCase` (escopo por papel)

**Files:** `src/modules/agenda/application/list_agenda.py` + `tests/unit/agenda/test_list_agenda.py`

> Gestor = `client` **ou** `shop_role='gerente'` vê tudo (espelha `isAgendaGestor`). Demais veem vendedor/responsável/sem responsável (com permissão).

- [ ] **Step 1: Teste com fakes**

`tests/unit/agenda/test_list_agenda.py`:
```python
import pytest
from dataclasses import dataclass
from src.modules.agenda.application.list_agenda import ListAgendaUseCase


@dataclass
class Cur:
    user_id: str
    role: str
    parent_store_id: str | None = None


@dataclass
class DomainUser:
    shop_role: str | None
    can_see_unassigned_leads: bool


class FakeUsers:
    def __init__(self, u): self.u = u
    async def get_by_id(self, uid): return self.u


class FakeReader:
    def __init__(self): self.scope = None
    async def query(self, **kw):
        self.scope = kw["scope"]
        return [], 0


@pytest.mark.asyncio
async def test_client_is_gestor() -> None:
    reader = FakeReader()
    uc = ListAgendaUseCase(reader, FakeUsers(DomainUser("vendedor", False)))
    await uc.execute(Cur("u1", "client"), {"store_id": "s1"})
    assert reader.scope["gestor"] is True


@pytest.mark.asyncio
async def test_shop_user_non_gestor_scope() -> None:
    reader = FakeReader()
    uc = ListAgendaUseCase(reader, FakeUsers(DomainUser("vendedor", True)))
    await uc.execute(Cur("u2", "shop_user", "s1"), {"store_id": "s1"})
    assert reader.scope["gestor"] is False
    assert reader.scope["user_id"] == "u2"
    assert reader.scope["include_unassigned"] is True


@pytest.mark.asyncio
async def test_gerente_is_gestor() -> None:
    reader = FakeReader()
    uc = ListAgendaUseCase(reader, FakeUsers(DomainUser("gerente", False)))
    await uc.execute(Cur("u3", "shop_user", "s1"), {"store_id": "s1"})
    assert reader.scope["gestor"] is True
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/agenda/application/list_agenda.py`:
```python
from src.modules.agenda.domain.period import AgendaPeriod


class ListAgendaUseCase:
    def __init__(self, reader, users) -> None:
        self._reader = reader
        self._users = users
        self._period = AgendaPeriod()

    async def execute(self, current, query: dict) -> dict:
        gestor = current.role == "client"
        include_unassigned = False
        if current.role == "shop_user":
            u = await self._users.get_by_id(current.user_id)
            gestor = bool(u and u.shop_role == "gerente")
            include_unassigned = bool(u and u.can_see_unassigned_leads)
        elif current.role == "admin":
            gestor = True

        apply_to = query.get("apply_to") or "agendamento"
        date_field = self._period.date_field(apply_to)
        date_from, date_to = self._period.resolve_range(query.get("preset") or "month", query.get("from") or "", query.get("to") or "")

        page = int(query.get("page") or 1)
        raw_size = int(query.get("page_size") or 25)
        page_size = raw_size if raw_size in (25, 50, 100) else 25

        items, total = await self._reader.query(
            store_id=query["store_id"], apply_to=apply_to, date_field=date_field,
            date_from=date_from, date_to=date_to,
            scope={"gestor": gestor, "user_id": current.user_id, "include_unassigned": include_unassigned},
            search=query.get("search"), page=page, page_size=page_size,
        )
        return {"items": items, "total": total, "page": page, "page_size": page_size}
```
```bash
uv run pytest tests/unit/agenda/test_list_agenda.py
git add -A && git commit -m "feat(agenda): add list agenda use case"
```

---

## Task 4: Router + wiring + e2e

**Files:** `src/modules/agenda/interface/{deps.py,router.py}`, `src/main.py`, `tests/e2e/test_agenda.py`

- [ ] **Step 1: deps + router**

`src/modules/agenda/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.agenda.application.list_agenda import ListAgendaUseCase
from src.modules.agenda.infrastructure.reader import AgendaReader
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.shared.infrastructure.database import get_session


def get_list_agenda_uc(session: AsyncSession = Depends(get_session)) -> ListAgendaUseCase:
    return ListAgendaUseCase(AgendaReader(session), SqlAlchemyUserRepository(session))
```
`src/modules/agenda/interface/router.py`:
```python
from fastapi import APIRouter, Depends, Query
from src.modules.agenda.application.list_agenda import ListAgendaUseCase
from src.modules.agenda.interface.deps import get_list_agenda_uc
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("")
async def list_agenda(
    store_id: str = Query(...),
    apply_to: str = Query("agendamento"),
    preset: str = Query("month"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(25),
    user: CurrentUser = Depends(get_current_user),
    uc: ListAgendaUseCase = Depends(get_list_agenda_uc),
) -> dict:
    return await uc.execute(user, {"store_id": store_id, "apply_to": apply_to, "preset": preset,
                                   "from": from_, "to": to, "search": search, "page": page, "page_size": page_size})
```
Em `src/main.py`, inclua `from src.modules.agenda.interface.router import router as agenda_router` e `app.include_router(agenda_router)`.

- [ ] **Step 2: e2e**

`tests/e2e/test_agenda.py`:
```python
import pytest


async def _admin(client):
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_agenda_empty_ok(client) -> None:
    headers = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Ag"}, headers=headers)).json()
    res = await client.get(f"/agenda?store_id={store['id']}&apply_to=agendamento&preset=month", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == [] and body["total"] == 0 and body["page"] == 1
```

- [ ] **Step 3: Rodar + commit + concluir**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(agenda): add agenda endpoint"
```
Atualize o status do Plano 07 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Resultado

- Agenda via API espelhando a tela: leads completos, filtros por tipo/preset, busca, paginação e escopo por papel. Atribuição de vendedor usa `PATCH /crm/leads/{id}`.

**Próximo:** [`08-metrics.md`](./08-metrics.md).
