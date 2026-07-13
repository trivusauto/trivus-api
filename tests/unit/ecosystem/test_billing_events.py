import pytest

from src.modules.ecosystem.application.billing_events import HandleBillingEventUseCase
from src.shared.domain.errors import DomainError


class FakeSubs:
    def __init__(self, mode: str = "gateway") -> None:
        self.mode = mode
        self.status_set: str | None = None

    async def get_or_raise(self, sid: object) -> dict[str, object]:
        return {"id": str(sid), "status": "active", "billing_mode": self.mode}

    async def update(self, sid: str, data: dict[str, object]) -> dict[str, object]:
        self.status_set = str(data.get("status"))
        return {"id": sid, **data}


class FakePayments:
    def __init__(self) -> None:
        self.saved: dict[str, object] | None = None

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        self.saved = data
        return {"id": "pay1", **data}


@pytest.mark.asyncio
async def test_confirmed_activates() -> None:
    subs, pays = FakeSubs(), FakePayments()
    uc = HandleBillingEventUseCase(subs, pays)
    await uc.execute({"subscription_id": "s1", "event_type": "payment_confirmed", "amount": 500})
    assert pays.saved is not None and pays.saved["event_type"] == "payment_confirmed"
    assert subs.status_set == "active"


@pytest.mark.asyncio
async def test_overdue_suspends() -> None:
    subs = FakeSubs()
    await HandleBillingEventUseCase(subs, FakePayments()).execute(
        {"subscription_id": "s1", "event_type": "payment_overdue"})
    assert subs.status_set == "suspended"


@pytest.mark.asyncio
async def test_manual_mode_only_records() -> None:
    subs = FakeSubs(mode="manual")
    pays = FakePayments()
    await HandleBillingEventUseCase(subs, pays).execute(
        {"subscription_id": "s1", "event_type": "payment_confirmed"})
    assert pays.saved is not None
    assert subs.status_set is None          # registra o pagamento mas não mexe no status


@pytest.mark.asyncio
async def test_unknown_event_rejected() -> None:
    with pytest.raises(DomainError, match="event_type"):
        await HandleBillingEventUseCase(FakeSubs(), FakePayments()).execute(
            {"subscription_id": "s1", "event_type": "whatever"})
