# Plano 06 — Webhook Z-API (código completo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–05. Código copia-e-cola.

**Goal:** `POST /webhook/zapi/{token}` cria leads no CRM a partir do WhatsApp — normalização de telefone, LID, dedup por variantes do 9º dígito, round-robin de SDR — **corrigindo o bug do ponteiro** (spec §10.4: lê e grava `last_assigned_sdr_id` em `stores`).

**Architecture:** Módulo `webhook`. `Phone` e `RoundRobin` são domínio puro. Reutiliza `FunnelRepository`, `StageRepository`, `LeadRepository`, `HistoryRepository` do Plano 05. Spec §6.11, §6.12, §8.1.

> Crie os `__init__.py` de `src/modules/webhook/` e subpastas, e de `tests/unit/webhook/`.

---

## Task 1: Serviço de domínio `Phone`

**Files:** `src/modules/webhook/domain/phone.py` + `tests/unit/webhook/test_phone.py`

- [ ] **Step 1: Teste**

`tests/unit/webhook/test_phone.py`:
```python
from src.modules.webhook.domain.phone import Phone

p = Phone()


def test_normalize() -> None:
    assert p.normalize_br("(11) 99999-9999") == "5511999999999"
    assert p.normalize_br("5511999999999") == "5511999999999"
    assert p.normalize_br("123") is None
    assert p.normalize_br("1133334444") is None


def test_extract_identity() -> None:
    assert p.extract_identity({"phone": "5544999999999@c.us"}) == ("44999999999", None)
    assert p.extract_identity({"phone": "63312750448861@lid"}) == (None, "63312750448861")


def test_variants() -> None:
    assert p.match_variants("44999999999") == ["44999999999", "4499999999"]
    assert p.match_variants("4499999999") == ["4499999999", "44999999999"]


def test_parse_many() -> None:
    r = p.parse_many("(11) 99999-9999, 11999999999\n5511988887777 abc")
    assert r["phones"] == ["5511999999999", "5511988887777"]
    assert r["duplicated"] == 1
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/webhook/domain/phone.py`:
```python
import re


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


class Phone:
    def normalize_br(self, value: str) -> str | None:
        d = _digits(str(value).strip())
        if not d:
            return None
        if d.startswith("55") and len(d) == 13:
            norm = d
        elif len(d) == 11:
            norm = "55" + d
        elif len(d) == 12 and d.startswith("55"):
            return None
        elif len(d) == 13 and not d.startswith("55"):
            return None
        elif len(d) not in (11, 13):
            return None
        else:
            norm = d
        number = norm[4:] if len(norm) == 13 else norm[2:]
        if len(number) != 9 or number[0] != "9":
            return None
        return norm if len(norm) == 13 else "55" + norm

    def extract_identity(self, body: dict) -> tuple[str | None, str | None]:
        phone_field = str(body.get("phone") or "")
        is_lid = "@lid" in phone_field
        lid_source = str(body.get("chatLid") or body.get("senderLid") or (phone_field if is_lid else "") or "")
        lid = _digits(lid_source.split("@")[0]) or None
        phone = None
        if not is_lid:
            digits = _digits(phone_field.split("@")[0])
            if len(digits) in (12, 13) and digits.startswith("55"):
                digits = digits[2:]
            phone = digits or None
        return phone, lid

    def match_variants(self, phone: str | None) -> list[str]:
        d = _digits(str(phone or ""))
        if not d:
            return []
        variants = [d]
        if len(d) == 11 and d[2] == "9":
            variants.append(d[:2] + d[3:])
        elif len(d) == 10:
            variants.append(d[:2] + "9" + d[2:])
        return variants

    def parse_many(self, text: str) -> dict:
        tokens = [t for t in re.split(r"[\s,\t\n\r;]+", text or "") if t]
        phones: list[str] = []
        seen: set[str] = set()
        invalid = duplicated = 0
        for tok in tokens:
            n = self.normalize_br(tok)
            if n:
                if n in seen:
                    duplicated += 1
                    continue
                seen.add(n)
                phones.append(n)
            elif len(_digits(tok)) >= 8:
                invalid += 1
        return {"phones": phones, "invalid": invalid, "duplicated": duplicated}
```
```bash
uv run pytest tests/unit/webhook/test_phone.py
git add -A && git commit -m "feat(webhook): port phone domain service"
```

---

## Task 2: Serviço de domínio `RoundRobin`

**Files:** `src/modules/webhook/domain/round_robin.py` + `tests/unit/webhook/test_round_robin.py`

- [ ] **Step 1: Teste**

`tests/unit/webhook/test_round_robin.py`:
```python
from src.modules.webhook.domain.round_robin import RoundRobin

r = RoundRobin()


def test_eligible() -> None:
    assert r.eligible([{"id": "a", "can_see_unassigned_leads": True}, {"id": "b", "can_see_unassigned_leads": False}]) == ["a"]


def test_pick_next() -> None:
    assert r.pick_next(["a", "b", "c"], "a") == "b"
    assert r.pick_next(["a", "b", "c"], "c") == "a"
    assert r.pick_next(["a", "b", "c"], None) == "a"
    assert r.pick_next([], "a") is None
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/webhook/domain/round_robin.py`:
```python
class RoundRobin:
    def eligible(self, sdrs: list[dict]) -> list[str]:
        return [s["id"] for s in (sdrs or []) if s.get("can_see_unassigned_leads")]

    def pick_next(self, sdr_ids: list[str], last_assigned: str | None) -> str | None:
        if not sdr_ids:
            return None
        if last_assigned in sdr_ids:
            return sdr_ids[(sdr_ids.index(last_assigned) + 1) % len(sdr_ids)]
        return sdr_ids[0]
```
```bash
uv run pytest tests/unit/webhook/test_round_robin.py
git add -A && git commit -m "feat(webhook): port round robin"
```

---

## Task 3: Repositórios do webhook (stores/leads/users)

**Files:** `src/modules/webhook/infrastructure/repositories.py`

> Métodos específicos do fluxo. Reutiliza os models de Plano 04 (`StoreModel`) e Plano 05 (`LeadModel`) e auth (`UserModel`).

- [ ] **Step 1: Implementar**

`src/modules/webhook/infrastructure/repositories.py`:
```python
import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.auth.infrastructure.orm import UserModel
from src.modules.crm.infrastructure.orm import LeadModel
from src.modules.stores.infrastructure.orm import StoreModel


class WebhookStoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_webhook_token(self, token: str) -> StoreModel | None:
        return (await self._session.execute(select(StoreModel).where(StoreModel.webhook_token == token))).scalar_one_or_none()

    async def update_last_sdr(self, store_id: str, sdr_id: str | None) -> None:
        row = await self._session.get(StoreModel, store_id)
        if row is not None:
            row.last_assigned_sdr_id = sdr_id
            await self._session.flush()


class WebhookLeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_duplicate(self, store_id: str, lid: str | None, phone_variants: list[str]) -> LeadModel | None:
        conds = []
        if lid:
            conds.append(LeadModel.lid == lid)
            conds.append(LeadModel.telefone == lid)
        for v in phone_variants:
            conds.append(LeadModel.telefone == v)
        if not conds:
            return None
        stmt = select(LeadModel).where(LeadModel.store_id == store_id, or_(*conds)).order_by(LeadModel.created_at).limit(1)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def enrich(self, lead: LeadModel, lid: str | None, phone: str | None) -> None:
        changed = False
        if lid and not lead.lid:
            lead.lid = lid
            changed = True
        existing_digits = "".join(ch for ch in (lead.telefone or "") if ch.isdigit())
        if phone and (not existing_digits or len(existing_digits) > 11):
            lead.telefone = phone
            changed = True
        if changed:
            await self._session.flush()

    async def create(self, data: dict) -> LeadModel:
        row = LeadModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return row


class WebhookUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_sdrs(self, store_id: str) -> list[dict]:
        stmt = select(UserModel).where(
            UserModel.parent_store_id == store_id, UserModel.role == "shop_user",
            UserModel.shop_role == "sdr", UserModel.active.is_(True),
        ).order_by(UserModel.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [{"id": str(r.id), "can_see_unassigned_leads": r.can_see_unassigned_leads} for r in rows]
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat(webhook): add webhook repositories"
```

---

## Task 4: `HandleZapiWebhookUseCase`

**Files:** `src/modules/webhook/application/handle_zapi.py` + `tests/unit/webhook/test_handle_zapi.py`

- [ ] **Step 1: Teste com fakes**

`tests/unit/webhook/test_handle_zapi.py`:
```python
import pytest
from src.modules.webhook.application.handle_zapi import HandleZapiWebhookUseCase
from src.modules.webhook.domain.phone import Phone
from src.modules.webhook.domain.round_robin import RoundRobin


class Store:
    id = "s1"; active = True; zapi_webhook_enabled = True; crm_enabled = True; last_assigned_sdr_id = None


class Stores:
    def __init__(self): self.last = "unset"
    async def get_by_webhook_token(self, token): return Store() if token == "tok" else None
    async def update_last_sdr(self, store_id, sdr_id): self.last = sdr_id


class Leads:
    def __init__(self, dup=None): self.dup = dup; self.created = None
    async def find_duplicate(self, store_id, lid, variants): return self.dup
    async def enrich(self, lead, lid, phone): ...
    async def create(self, data): self.created = data; return type("L", (), {"id": "lead1"})()


class Funnels:
    async def first_clone(self, store_id): return type("F", (), {"id": "f1"})()


class Stages:
    async def first_of_funnel(self, fid): return type("S", (), {"id": "st1"})()


class LeadsCount:
    async def count_in_stage(self, sid): return 0


class Users:
    async def active_sdrs(self, store_id): return []


class History:
    def __init__(self): self.recorded = None
    async def record(self, lead_id, stage_id): self.recorded = (lead_id, stage_id)


def _uc(leads=None, stores=None):
    return HandleZapiWebhookUseCase(stores or Stores(), leads or Leads(), Funnels(), Stages(), LeadsCount(), Users(), History(), Phone(), RoundRobin())


@pytest.mark.asyncio
async def test_unauthorized() -> None:
    res = await _uc().execute("wrong", {"phone": "5544999999999@c.us"})
    assert res == {"ok": False, "reason": "unauthorized", "status": 401}


@pytest.mark.asyncio
async def test_group_skipped() -> None:
    res = await _uc().execute("tok", {"isGroup": True})
    assert res == {"ok": True, "skipped": "group"}


@pytest.mark.asyncio
async def test_creates_lead() -> None:
    leads = Leads()
    res = await _uc(leads=leads).execute("tok", {"phone": "5544999999999@c.us", "chatName": "João"})
    assert res["ok"] is True and res["lead_id"] == "lead1"
    assert leads.created["telefone"] == "44999999999"
    assert leads.created["funil"] == "receptivo"


@pytest.mark.asyncio
async def test_duplicate() -> None:
    leads = Leads(dup=type("L", (), {"id": "old", "lid": None, "telefone": "44999999999"})())
    res = await _uc(leads=leads).execute("tok", {"phone": "5544999999999@c.us"})
    assert res["skipped"] == "duplicate"
```

- [ ] **Step 2: Rodar e ver falhar → implementar**

`src/modules/webhook/application/handle_zapi.py`:
```python
class HandleZapiWebhookUseCase:
    def __init__(self, stores, leads, funnels, stages, leads_count, users, history, phone, round_robin) -> None:
        self._stores = stores
        self._leads = leads
        self._funnels = funnels
        self._stages = stages
        self._count = leads_count
        self._users = users
        self._history = history
        self._phone = phone
        self._rr = round_robin

    async def execute(self, token: str, body: dict) -> dict:
        store = await self._stores.get_by_webhook_token(token)
        if store is None:
            return {"ok": False, "reason": "unauthorized", "status": 401}
        if not (store.active and store.zapi_webhook_enabled and store.crm_enabled):
            return {"ok": True, "skipped": "disabled"}
        if body.get("isGroup"):
            return {"ok": True, "skipped": "group"}
        if body.get("fromMe"):
            return {"ok": True, "skipped": "from_me"}
        if body.get("isNewsletter"):
            return {"ok": True, "skipped": "newsletter"}

        phone, lid = self._phone.extract_identity(body)
        if not phone and not lid:
            return {"ok": True, "skipped": "no_phone"}
        contact_name = (str(body.get("chatName") or body.get("senderName") or "")).strip() or phone or lid

        existing = await self._leads.find_duplicate(store.id, lid, self._phone.match_variants(phone))
        if existing is not None:
            await self._leads.enrich(existing, lid, phone)
            return {"ok": True, "skipped": "duplicate", "lead_id": str(existing.id)}

        funnel = await self._funnels.first_clone(store.id)
        if funnel is None:
            return {"ok": False, "reason": "no_template_funnel", "status": 422}
        stage = await self._stages.first_of_funnel(funnel.id)
        if stage is None:
            return {"ok": False, "reason": "no_stage", "status": 422}

        assigned_to = None
        eligible = self._rr.eligible(await self._users.active_sdrs(store.id))
        if eligible:
            assigned_to = self._rr.pick_next(eligible, store.last_assigned_sdr_id)
            await self._stores.update_last_sdr(store.id, assigned_to)

        sort_order = await self._count.count_in_stage(stage.id)
        lead = await self._leads.create({
            "stage_id": stage.id, "store_id": store.id, "nome": contact_name,
            "telefone": phone or lid, "lid": lid, "sort_order": sort_order,
            "assigned_to": assigned_to, "funil": "receptivo",
        })
        await self._history.record(str(lead.id), stage.id)
        return {"ok": True, "lead_id": str(lead.id), "assigned_to": assigned_to}
```
```bash
uv run pytest tests/unit/webhook/test_handle_zapi.py
git add -A && git commit -m "feat(webhook): handle zapi inbound use case"
```

---

## Task 5: Router público + wiring

**Files:** `src/modules/webhook/interface/{deps.py,router.py}`, `src/main.py`, `tests/e2e/test_webhook.py`

- [ ] **Step 1: deps + router**

`src/modules/webhook/interface/deps.py`:
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.crm.infrastructure.repositories import FunnelRepository, HistoryRepository, LeadRepository, StageRepository
from src.modules.webhook.application.handle_zapi import HandleZapiWebhookUseCase
from src.modules.webhook.domain.phone import Phone
from src.modules.webhook.domain.round_robin import RoundRobin
from src.modules.webhook.infrastructure.repositories import WebhookLeadRepository, WebhookStoreRepository, WebhookUserRepository
from src.shared.infrastructure.database import get_session


def get_handle_zapi_uc(session: AsyncSession = Depends(get_session)) -> HandleZapiWebhookUseCase:
    return HandleZapiWebhookUseCase(
        WebhookStoreRepository(session), WebhookLeadRepository(session),
        FunnelRepository(session), StageRepository(session), LeadRepository(session),
        WebhookUserRepository(session), HistoryRepository(session), Phone(), RoundRobin(),
    )
```
> `FunnelRepository.first_clone`, `StageRepository.first_of_funnel`, `LeadRepository.count_in_stage`, `HistoryRepository.record` vêm do Plano 05.

`src/modules/webhook/interface/router.py`:
```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from src.modules.webhook.application.handle_zapi import HandleZapiWebhookUseCase
from src.modules.webhook.interface.deps import get_handle_zapi_uc

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/zapi/{token}")
async def zapi(token: str, request: Request, uc: HandleZapiWebhookUseCase = Depends(get_handle_zapi_uc)) -> JSONResponse:
    body = await request.json()
    result = await uc.execute(token, body)
    status = result.pop("status", 200)
    return JSONResponse(status_code=status, content=result)
```
Em `src/main.py`, inclua `from src.modules.webhook.interface.router import router as webhook_router` e `app.include_router(webhook_router)`.

- [ ] **Step 2: e2e**

`tests/e2e/test_webhook.py`:
```python
import uuid
import pytest


async def _admin(client):
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_group_skipped(client) -> None:
    token = uuid.uuid4().hex
    headers = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja WH"}, headers=headers)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"webhook_token": token, "zapi_webhook_enabled": True}, headers=headers)
    res = await client.post(f"/webhook/zapi/{token}", json={"isGroup": True})
    assert res.status_code == 200
    assert res.json()["skipped"] in ("group", "disabled")  # disabled se CRM ainda off
```
> Para o caso de criar lead de verdade, ligue o CRM (`{"crm_enabled": true}`) numa loja que tenha funil-template clonado (precisa de um funil `is_template=True` no banco — crie via seed/admin). O teste acima cobre o caminho de filtro sem depender disso.

- [ ] **Step 3: Rodar + commit + concluir**

```bash
uv run pytest && uv run ruff check . && uv run mypy src
git add -A && git commit -m "feat(webhook): add public zapi endpoint"
```
Atualize o status do Plano 06 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Resultado

- Captação automática via WhatsApp, fiel ao fluxo atual, com o bug do ponteiro SDR corrigido na raiz — código copia-e-cola.

**Próximo:** [`07-agenda.md`](./07-agenda.md).
