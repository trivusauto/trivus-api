import pytest

from src.modules.ecosystem.application.store_services import ToggleStoreServiceUseCase
from src.modules.ecosystem.application.subscriptions import CreateSubscriptionUseCase
from src.shared.domain.errors import DomainError


class FakeSubs:
    def __init__(self, current: dict[str, object] | None = None) -> None:
        self.current = current
        self.created: dict[str, object] | None = None

    async def current_for_company(self, cid: str) -> dict[str, object] | None:
        return self.current

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        self.created = data
        return {"id": "sub1", **data}


class FakePlans:
    async def get_or_raise(self, pid: str) -> dict[str, object]:
        return {"id": pid, "key": "pro", "service_keys": ["crm_completo"], "max_stores": 2}


class FakeCompanyStores:
    def __init__(self, n: int) -> None:
        self.n = n

    async def count_stores(self, company_id: str) -> int:
        return self.n

    async def store_company(self, store_id: str) -> str | None:
        return "c1"


class FakeStoreServices:
    def __init__(self) -> None:
        self.set_args: tuple[str, str, bool] | None = None

    async def set_service(self, store_id: str, service_key: str, enabled: bool) -> None:
        self.set_args = (store_id, service_key, enabled)


@pytest.mark.asyncio
async def test_create_subscription_trialing_requires_trial_end() -> None:
    uc = CreateSubscriptionUseCase(FakeSubs(), FakePlans(), FakeCompanyStores(1))
    with pytest.raises(DomainError, match="trial"):
        await uc.execute({"company_id": "c1", "plan_id": "p1", "status": "trialing"})


@pytest.mark.asyncio
async def test_create_subscription_max_stores() -> None:
    uc = CreateSubscriptionUseCase(FakeSubs(), FakePlans(), FakeCompanyStores(3))
    with pytest.raises(DomainError, match="lojas"):
        await uc.execute({"company_id": "c1", "plan_id": "p1", "status": "active"})


@pytest.mark.asyncio
async def test_create_subscription_ok() -> None:
    subs = FakeSubs()
    res = await CreateSubscriptionUseCase(subs, FakePlans(), FakeCompanyStores(1)).execute(
        {"company_id": "c1", "plan_id": "p1", "status": "active"})
    assert res["id"] == "sub1"
    assert subs.created is not None and subs.created["billing_mode"] == "manual"


@pytest.mark.asyncio
async def test_toggle_service_not_in_plan() -> None:
    subs = FakeSubs(current={"id": "s", "status": "active", "plan_id": "p1"})
    uc = ToggleStoreServiceUseCase(FakeStoreServices(), subs, FakePlans(), FakeCompanyStores(1))
    with pytest.raises(DomainError, match="plano"):
        await uc.execute("store1", "metricas_avancadas", True)


@pytest.mark.asyncio
async def test_toggle_service_in_plan_ok() -> None:
    subs = FakeSubs(current={"id": "s", "status": "active", "plan_id": "p1"})
    store_services = FakeStoreServices()
    uc = ToggleStoreServiceUseCase(store_services, subs, FakePlans(), FakeCompanyStores(1))
    await uc.execute("store1", "crm_completo", True)
    assert store_services.set_args == ("store1", "crm_completo", True)


@pytest.mark.asyncio
async def test_toggle_off_always_allowed() -> None:
    store_services = FakeStoreServices()
    uc = ToggleStoreServiceUseCase(store_services, FakeSubs(), FakePlans(), FakeCompanyStores(1))
    await uc.execute("store1", "crm_completo", False)
    assert store_services.set_args == ("store1", "crm_completo", False)
