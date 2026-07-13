import pytest
from src.modules.webhook.application.handle_zapi import HandleZapiWebhookUseCase
from src.modules.webhook.domain.phone import Phone
from src.modules.webhook.domain.round_robin import RoundRobin


class Store:
    id = "s1"
    active = True
    zapi_webhook_enabled = True
    crm_enabled = True
    last_assigned_sdr_id = None


class Stores:
    def __init__(self) -> None:
        self.last: object = "unset"

    async def get_by_webhook_token(self, token: str) -> object:
        return Store() if token == "tok" else None

    async def update_last_sdr(self, store_id: str, sdr_id: str | None) -> None:
        self.last = sdr_id


class Leads:
    def __init__(self, dup: object = None) -> None:
        self.dup = dup
        self.created: dict[str, object] | None = None

    async def find_duplicate(self, store_id: str, lid: object, variants: list[str]) -> object:
        return self.dup

    async def enrich(self, lead: object, lid: object, phone: object) -> None: ...

    async def create(self, data: dict[str, object]) -> object:
        self.created = data
        return type("L", (), {"id": "lead1"})()


class Funnels:
    async def first_clone(self, store_id: str) -> object:
        return type("F", (), {"id": "f1"})()


class Stages:
    async def first_of_funnel(self, fid: str) -> object:
        return type("S", (), {"id": "st1"})()


class LeadsCount:
    async def count_in_stage(self, sid: str) -> int:
        return 0


class Users:
    async def active_sdrs(self, store_id: str) -> list[object]:
        return []


class History:
    def __init__(self) -> None:
        self.recorded: tuple[str, str] | None = None

    async def record(self, lead_id: str, stage_id: str) -> None:
        self.recorded = (lead_id, stage_id)


def _uc(leads: object = None, stores: object = None) -> HandleZapiWebhookUseCase:
    return HandleZapiWebhookUseCase(stores or Stores(), leads or Leads(), Funnels(), Stages(), LeadsCount(), Users(), History(), Phone(), RoundRobin())  # type: ignore[arg-type]


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
    assert leads.created is not None
    assert leads.created["telefone"] == "44999999999"
    assert leads.created["funil"] == "receptivo"


@pytest.mark.asyncio
async def test_duplicate() -> None:
    leads = Leads(dup=type("L", (), {"id": "old", "lid": None, "telefone": "44999999999"})())
    res = await _uc(leads=leads).execute("tok", {"phone": "5544999999999@c.us"})
    assert res["skipped"] == "duplicate"


class MatcherHit:
    async def match(self, store_id: str, body: dict[str, object]) -> str:
        return "camp1"


@pytest.mark.asyncio
async def test_creates_lead_with_campaign() -> None:
    leads = Leads()
    uc = HandleZapiWebhookUseCase(Stores(), leads, Funnels(), Stages(), LeadsCount(), Users(), History(),
                                  Phone(), RoundRobin(), campaign_matcher=MatcherHit())
    await uc.execute("tok", {"phone": "5544999999999@c.us"})
    assert leads.created is not None and leads.created["campaign_id"] == "camp1"
