import pytest

from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase


def lead(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "l1", "created_at": "2026-07-10T12:00:00Z", "funil": "receptivo", "stage_id": None,
        "campaign_id": None, "data_agendamento": None, "hora_agendamento": None,
        "data_marcacao_agendamento": None, "compareceu_agendamento": False, "data_compareceu": None,
        "fechou_negocio": False, "data_fechou_negocio": None, "rentabilidade": None,
    }
    base.update(over)
    return base


class FakeReader:
    def __init__(self, leads: list[dict[str, object]]) -> None:
        self.leads = leads

    async def leads_for_stores(self, ids: list[str]) -> list[dict[str, object]]:
        return self.leads


class _Ctx:
    @staticmethod
    def passed(lead: dict[str, object]) -> bool:
        return True


class FakeReach:
    async def build(self, ids: list[str], stage: str) -> _Ctx:
        return _Ctx()


class FakeInvestment:
    async def total(self, ids: list[str], start: str, end: str) -> float:
        return 1000.0


class _Camp:
    id = "camp1"
    budget = 400.0


class FakeCampaigns:
    async def get(self, cid: str) -> _Camp:
        return _Camp()


class FakeGoals:
    async def list(self, store_id: str, year: int, month: int) -> list[dict[str, object]]:
        return [{"origin": "receptivo", "leads_quantity": 2, "conversions_quantity": 1,
                 "marketing_investment_goal": 1200}]


def make(leads: list[dict[str, object]]) -> MarketingFunnelUseCase:
    return MarketingFunnelUseCase(FakeReader(leads), FakeReach(), FakeInvestment(), FakeCampaigns(), FakeGoals())


@pytest.mark.asyncio
async def test_receptivo_only_and_costs() -> None:
    leads = [lead(), lead(id="l2", funil="prospeccao_ativa")]   # prospecção fica de fora
    f = await make(leads).execute(["s1"], "2026-07-01", "2026-07-31")
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["quantity"] == 1
    assert stages["leads"]["unit_cost"] == 1000.0


@pytest.mark.asyncio
async def test_campaign_filter_uses_budget() -> None:
    leads = [lead(campaign_id="camp1"), lead(id="l2")]
    f = await make(leads).execute(["s1"], "2026-07-01", "2026-07-31", campaign_id="camp1")
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["quantity"] == 1
    assert f["investment"] == 400.0                       # budget da campanha (D3)


@pytest.mark.asyncio
async def test_lights_from_goals() -> None:
    f = await make([lead()]).execute(["s1"], "2026-07-01", "2026-07-31")
    stages = {s["stage"]: s for s in f["stages"]}
    assert stages["leads"]["light"] == "red"              # 1 de meta 2 = 50%
    assert stages["classified"]["light"] == "gray"        # classificados não tem meta
    assert f["investment_goal"] == 1200.0


@pytest.mark.asyncio
async def test_lights_gray_when_multi_month() -> None:
    f = await make([lead()]).execute(["s1"], "2026-06-01", "2026-07-31")
    assert all(s["light"] == "gray" for s in f["stages"])   # período > 1 mês (D6)
