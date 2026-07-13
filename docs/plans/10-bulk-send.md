# Plano 10 — Disparos em massa (código completo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–04 e 06 (fornece `Phone`). Código copia-e-cola.

**Goal:** Criar/gerenciar disparos de WhatsApp — validar/dedup telefones (via `Phone.parse_many`), persistir `bulk_sends` + `bulk_send_contacts`, disparar o n8n a partir do **servidor**, e endpoint (token de integração) para o n8n atualizar status. Spec §4.9, §6.12, §8.2.

**Architecture:** Módulo `bulk_send`. Reutiliza `Phone` (Plano 06).

> Crie os `__init__.py` de `src/modules/bulk_send/` e subpastas, e das pastas de teste.

---

## Task 1: ORM + repositórios

**Files:** `src/modules/bulk_send/infrastructure/{orm.py,repository.py}`

- [ ] **Step 1: ORM**

`src/modules/bulk_send/infrastructure/orm.py`:
```python
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from src.shared.infrastructure.database import Base


class BulkSendModel(Base):
    __tablename__ = "bulk_sends"
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    total_contacts: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="draft")
    message_template: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_1: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_2: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_3: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_4: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_5: Mapped[str | None] = mapped_column(String, nullable=True)
    delay_min_sec: Mapped[int] = mapped_column(Integer, default=30)
    delay_max_sec: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BulkSendContactModel(Base):
    __tablename__ = "bulk_send_contacts"
    id: Mapped[str] = mapped_column(primary_key=True)
    bulk_send_id: Mapped[str] = mapped_column(String)
    phone: Mapped[str] = mapped_column(String)
    variation_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
```

- [ ] **Step 2: Repositórios**

`src/modules/bulk_send/infrastructure/repository.py`:
```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.bulk_send.infrastructure.orm import BulkSendContactModel, BulkSendModel
from src.shared.domain.errors import NotFoundError


class BulkSendRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> str:
        row = BulkSendModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return str(row.id)

    async def list(self) -> list[dict]:
        rows = (await self._session.execute(select(BulkSendModel).order_by(BulkSendModel.created_at.desc()))).scalars().all()
        return [{"id": str(r.id), "title": r.title, "total_contacts": r.total_contacts, "status": r.status,
                 "success_count": r.success_count, "error_count": r.error_count} for r in rows]


class BulkSendContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, rows: list[dict]) -> None:
        for r in rows:
            self._session.add(BulkSendContactModel(id=str(uuid.uuid4()), **r))
        await self._session.flush()

    async def list_ordered(self, bulk_send_id: str) -> list[dict]:
        rank = case((BulkSendContactModel.status == "pending", 0), (BulkSendContactModel.status == "sent", 1), else_=2)
        rows = (await self._session.execute(select(BulkSendContactModel).where(BulkSendContactModel.bulk_send_id == bulk_send_id).order_by(rank))).scalars().all()
        return [{"id": str(r.id), "phone": r.phone, "status": r.status, "error_message": r.error_message} for r in rows]

    async def update_status(self, contact_id: str, status: str, error_message: str | None) -> None:
        row = await self._session.get(BulkSendContactModel, contact_id)
        if row is None:
            raise NotFoundError("Contato não encontrado")
        row.status = status
        row.error_message = error_message
        row.sent_at = datetime.now(timezone.utc) if status == "sent" else None
        await self._session.flush()
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat(bulk-send): add orm and repositories"
```

---

## Task 2: `CreateBulkSendUseCase`

**Files:** `src/modules/bulk_send/application/create.py` + `tests/unit/bulk_send/test_create.py`

- [ ] **Step 1: Teste com fakes**

`tests/unit/bulk_send/test_create.py`:
```python
import pytest
from src.modules.bulk_send.application.create import CreateBulkSendUseCase
from src.modules.webhook.domain.phone import Phone


class FakeSends:
    def __init__(self): self.data = None
    async def create(self, data): self.data = data; return "bs1"


class FakeContacts:
    def __init__(self): self.rows = None
    async def create_many(self, rows): self.rows = rows


@pytest.mark.asyncio
async def test_create_dedups_and_persists() -> None:
    sends, contacts = FakeSends(), FakeContacts()
    uc = CreateBulkSendUseCase(sends, contacts, Phone(), n8n=None)
    res = await uc.execute({"title": "T", "message_template": "oi", "variations": ["A", "B"],
                            "phones": ["11999999999", "11999999999", "5511988887777"],
                            "delay_min_sec": 30, "delay_max_sec": 30})
    assert sends.data["total_contacts"] == 2
    assert res["stats"]["duplicated"] == 1
    assert [c["variation_index"] for c in contacts.rows] == [0, 1]
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/bulk_send/application/create.py`:
```python
class CreateBulkSendUseCase:
    def __init__(self, sends, contacts, phone, n8n=None) -> None:
        self._sends = sends
        self._contacts = contacts
        self._phone = phone
        self._n8n = n8n

    async def execute(self, data: dict) -> dict:
        parsed = self._phone.parse_many("\n".join(data.get("phones", [])))
        phones = parsed["phones"]
        variations = (data.get("variations") or [])[:5]
        send_id = await self._sends.create({
            "title": data.get("title"), "message_template": data.get("message_template"),
            "status": "draft", "total_contacts": len(phones),
            "delay_min_sec": data.get("delay_min_sec", 30), "delay_max_sec": data.get("delay_max_sec", 30),
            "variation_1": variations[0] if len(variations) > 0 else None,
            "variation_2": variations[1] if len(variations) > 1 else None,
            "variation_3": variations[2] if len(variations) > 2 else None,
            "variation_4": variations[3] if len(variations) > 3 else None,
            "variation_5": variations[4] if len(variations) > 4 else None,
        })
        if phones:
            n = len(variations) or 1
            await self._contacts.create_many([
                {"bulk_send_id": send_id, "phone": p, "variation_index": i % n, "status": "pending"}
                for i, p in enumerate(phones)
            ])
        if self._n8n:
            await self._n8n.dispatch(send_id, data)
        return {"id": send_id, "stats": {"total": len(phones), "duplicated": parsed["duplicated"], "invalid": parsed["invalid"]}}
```
```bash
uv run pytest tests/unit/bulk_send/test_create.py
git add -A && git commit -m "feat(bulk-send): add create use case"
```

---

## Task 3: n8n client + router + status callback

**Files:** `src/modules/bulk_send/infrastructure/n8n_client.py`, `interface/{deps.py,router.py}`, `src/shared/infrastructure/settings.py`, `.env(.example)`, `src/main.py`, `tests/e2e/test_bulk_send.py`

- [ ] **Step 1: Settings do n8n**

Em `src/shared/infrastructure/settings.py`, adicione ao `Settings`:
```python
    n8n_bulk_send_webhook_url: str | None = None
    n8n_token: str = "dev-n8n-token"
```
E ao `.env`/`.env.example`:
```env
N8N_BULK_SEND_WEBHOOK_URL=
N8N_TOKEN=dev-n8n-token
```

- [ ] **Step 2: n8n client (dispara do servidor)**

`src/modules/bulk_send/infrastructure/n8n_client.py`:
```python
import httpx


class N8nClient:
    def __init__(self, url: str | None) -> None:
        self._url = url

    async def dispatch(self, send_id: str, data: dict) -> None:
        if not self._url:
            return  # sem env: salva no banco mas não chama (comportamento atual, spec §8.2)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(self._url, json={"bulk_send_id": send_id, "title": data.get("title")})
        except Exception:
            pass  # não bloqueia a criação do disparo
```

- [ ] **Step 3: Router (admin) + callback do n8n**

`src/modules/bulk_send/interface/deps.py`:
```python
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.bulk_send.application.create import CreateBulkSendUseCase
from src.modules.bulk_send.infrastructure.n8n_client import N8nClient
from src.modules.bulk_send.infrastructure.repository import BulkSendContactRepository, BulkSendRepository
from src.modules.webhook.domain.phone import Phone
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.settings import get_settings


def get_create_uc(session: AsyncSession = Depends(get_session)) -> CreateBulkSendUseCase:
    s = get_settings()
    return CreateBulkSendUseCase(BulkSendRepository(session), BulkSendContactRepository(session), Phone(), N8nClient(s.n8n_bulk_send_webhook_url))


def get_sends_repo(session: AsyncSession = Depends(get_session)) -> BulkSendRepository:
    return BulkSendRepository(session)


def get_contacts_repo(session: AsyncSession = Depends(get_session)) -> BulkSendContactRepository:
    return BulkSendContactRepository(session)


def require_n8n_token(x_n8n_token: str = Header(...)) -> None:
    if x_n8n_token != get_settings().n8n_token:
        raise HTTPException(status_code=401, detail="token inválido")
```
`src/modules/bulk_send/interface/router.py`:
```python
from fastapi import APIRouter, Body, Depends
from src.modules.bulk_send.application.create import CreateBulkSendUseCase
from src.modules.bulk_send.infrastructure.repository import BulkSendContactRepository, BulkSendRepository
from src.modules.bulk_send.interface.deps import get_contacts_repo, get_create_uc, get_sends_repo, require_n8n_token
from src.shared.interface.auth_deps import CurrentUser
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["bulk-send"])


@router.get("/admin/bulk-sends")
async def list_sends(_: CurrentUser = Depends(require_roles("admin")), repo: BulkSendRepository = Depends(get_sends_repo)) -> list[dict]:
    return await repo.list()


@router.post("/admin/bulk-sends", status_code=201)
async def create_send(body: dict = Body(...), _: CurrentUser = Depends(require_roles("admin")), uc: CreateBulkSendUseCase = Depends(get_create_uc)) -> dict:
    return await uc.execute(body)


@router.get("/admin/bulk-sends/{send_id}/logs")
async def logs(send_id: str, _: CurrentUser = Depends(require_roles("admin")), repo: BulkSendContactRepository = Depends(get_contacts_repo)) -> list[dict]:
    return await repo.list_ordered(send_id)


@router.patch("/integrations/bulk-send/contacts/{contact_id}/status", dependencies=[Depends(require_n8n_token)])
async def update_contact_status(contact_id: str, body: dict = Body(...), repo: BulkSendContactRepository = Depends(get_contacts_repo)) -> dict:
    await repo.update_status(contact_id, body["status"], body.get("error_message"))
    return {"ok": True}
```
Em `src/main.py`, inclua `from src.modules.bulk_send.interface.router import router as bulk_send_router` e `app.include_router(bulk_send_router)`.

- [ ] **Step 4: e2e + commit + concluir**

`tests/e2e/test_bulk_send.py`: admin `POST /admin/bulk-sends` com `{"title":"T","message_template":"oi","phones":["11999999999","5511988887777"]}` → 201 e `stats.total == 2`; `GET /admin/bulk-sends` lista; `GET .../logs` ordenado.
```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(bulk-send): add endpoints and n8n integration"
```
Atualize o status do Plano 10 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Resultado

- Disparos criados/listados via API, telefones validados no servidor, n8n disparado pelo backend e callback de status seguro.

**Próximo:** [`11-cleanup-cutover.md`](./11-cleanup-cutover.md) (operacional — ETL de exemplo + roteiro de virada).
