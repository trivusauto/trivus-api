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

    async def get(self, sid: str) -> object:
        return type("S", (), next(s for s in self.stages if s["id"] == sid))()

    async def list_for_funnel(self, fid: str) -> list[object]:
        return [type("S", (), s)() for s in self.stages]


class FakeHistory:
    def __init__(self) -> None:
        self.recorded: tuple[str, str] | None = None

    async def record(self, lead_id: str, stage_id: str) -> None:
        self.recorded = (lead_id, stage_id)


class FakeActivity:
    async def log(self, **kw: object) -> None:
        ...


class U:
    user_id = "u1"
    role = "client"


STAGES: list[dict[str, object]] = [
    {"id": "st0", "name": "RECEBIDOS", "funnel_id": "f1", "sort_order": 0},
    {"id": "st1", "name": "CLASSIFICADOS", "funnel_id": "f1", "sort_order": 1},
]


async def test_blocks_without_required_fields() -> None:
    leads = FakeLeads({"id": "l1", "store_id": "s1", "stage_id": "st0", "funil": "r", "telefone": "1"})
    uc = MoveLeadStageUseCase(leads, FakeStages(STAGES), FakeHistory(), FakeActivity(), StageRules())
    with pytest.raises(DomainError):
        await uc.execute("l1", "st1", U())


async def test_moves_with_fields() -> None:
    leads = FakeLeads({"id": "l1", "store_id": "s1", "stage_id": "st0", "funil": "r", "telefone": "1", "nome": "A", "cidade": "C"})
    hist = FakeHistory()
    uc = MoveLeadStageUseCase(leads, FakeStages(STAGES), hist, FakeActivity(), StageRules())
    await uc.execute("l1", "st1", U())
    assert leads.moved_to == "st1"
    assert hist.recorded == ("l1", "st1")
