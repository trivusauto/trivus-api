import pytest

from src.modules.crm.application.move_lead import MoveLeadStageUseCase
from src.modules.crm.domain.stage_rules import StageRules
from src.shared.domain.errors import DomainError


class FakeLeads:
    def __init__(self, lead: dict[str, object]) -> None:
        self.lead = lead
        self.moved_to: str | None = None

    async def get_or_raise(self, lead_id: str) -> dict[str, object]:
        return self.lead

    async def update(self, lead_id: str, data: dict[str, object]) -> dict[str, object]:
        self.moved_to = str(data["stage_id"])
        return {**self.lead, **data}


class FakeStages:
    def __init__(self, stages: list[dict[str, object]]) -> None:
        self.stages = stages

    async def get(self, sid: str):  # type: ignore[no-untyped-def]
        return next(type("S", (), s)() for s in self.stages if s["id"] == sid)

    async def list_for_funnel(self, fid: str):  # type: ignore[no-untyped-def]
        return [type("S", (), s)() for s in self.stages]


class FakeHistory:
    async def record(self, lead_id: str, stage_id: str) -> None:
        pass


class FakeActivity:
    async def log(self, **kw: object) -> None:
        pass


class FlagsOn:
    async def require_campaign(self, store_id: str) -> bool:
        return True


class U:
    user_id = "u1"
    role = "client"


STAGES: list[dict[str, object]] = [
    {"id": "st0", "name": "RECEBIDOS", "funnel_id": "f1", "sort_order": 0},
    {"id": "st1", "name": "CLASSIFICADOS", "funnel_id": "f1", "sort_order": 1},
]
BASE: dict[str, object] = {"id": "l1", "store_id": "s1", "stage_id": "st0", "funil": "receptivo",
                           "telefone": "1", "nome": "A", "cidade": "C", "campaign_id": None}


def make(lead: dict[str, object]) -> MoveLeadStageUseCase:
    return MoveLeadStageUseCase(FakeLeads(lead), FakeStages(STAGES), FakeHistory(), FakeActivity(),  # type: ignore[arg-type]
                                StageRules(), store_flags=FlagsOn())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_blocks_receptivo_without_campaign() -> None:
    with pytest.raises(DomainError, match="campanha"):
        await make(dict(BASE)).execute("l1", "st1", U())


@pytest.mark.asyncio
async def test_allows_with_campaign() -> None:
    moved = await make({**BASE, "campaign_id": "camp1"}).execute("l1", "st1", U())
    assert moved["stage_id"] == "st1"


@pytest.mark.asyncio
async def test_prospeccao_not_blocked() -> None:
    moved = await make({**BASE, "funil": "prospeccao_ativa"}).execute("l1", "st1", U())
    assert moved["stage_id"] == "st1"
