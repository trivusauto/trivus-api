import pytest
from src.modules.crm.application.sync_template import SyncTemplateToClientsUseCase


def stage(sid: str, name: str, order: int, tsid: str | None = None) -> object:
    return type("S", (), {"id": sid, "name": name, "sort_order": order, "template_stage_id": tsid})()


class FakeFunnels:
    def __init__(self) -> None:
        self.tpl = type("F", (), {"id": "tpl", "name": "Padrão Novo"})()
        self.clone = type("F", (), {"id": "cl", "name": "Antigo", "template_source_id": "tpl"})()
        self.renamed: str | None = None

    async def list_clones(self, template_id: str) -> list[object]:
        return [self.clone]

    async def get(self, fid: str) -> object | None:
        return self.tpl if fid == "tpl" else self.clone

    async def update_name(self, fid: str, name: str) -> None:
        self.renamed = name


class FakeStages:
    def __init__(self) -> None:
        self.tpl_stages: list[object] = [stage("t1", "RECEBIDOS", 0), stage("t2", "CLASSIFICADOS", 1)]
        self.client_stages: list[object] = [stage("c1", "RECEBIDOS", 0, "t1"), stage("c9", "COLUNA ANTIGA", 1, None)]
        self.created: list[object] = []
        self.deleted: list[str] = []
        self.updated: list[str] = []

    async def list_for_funnel(self, fid: str) -> list[object]:
        return self.tpl_stages if fid == "tpl" else list(self.client_stages)

    async def create(self, funnel_id: str, name: str, sort_order: int = 0, template_stage_id: str | None = None) -> object:
        s = stage(f"new-{name}", name, sort_order, template_stage_id)
        self.created.append(s)
        self.client_stages.append(s)
        return s

    async def update(self, stage_id: str, name: str | None = None, sort_order: int | None = None, template_stage_id: str | None = None) -> None:
        self.updated.append(stage_id)
        for s in self.client_stages:
            if s.id == stage_id and template_stage_id is not None:  # type: ignore[attr-defined]
                s.template_stage_id = template_stage_id  # type: ignore[attr-defined]

    async def delete(self, stage_id: str) -> None:
        self.deleted.append(stage_id)
        self.client_stages = [s for s in self.client_stages if s.id != stage_id]  # type: ignore[attr-defined]


class FakeCooling:
    async def copy(self, src: str, dst: str) -> None: ...
    async def delete_for_stage(self, sid: str) -> None: ...


class FakeLeads:
    def __init__(self) -> None:
        self.moves: list[tuple[str, str]] = []

    async def move_all_from_stage(self, frm: str, to: str) -> None:
        self.moves.append((frm, to))


@pytest.mark.asyncio
async def test_sync_creates_and_removes_orphan() -> None:
    funnels, stages, leads = FakeFunnels(), FakeStages(), FakeLeads()
    uc = SyncTemplateToClientsUseCase(funnels, stages, FakeCooling(), leads)
    await uc.execute("tpl")
    assert funnels.renamed == "Padrão Novo"
    assert any(s.name == "CLASSIFICADOS" for s in stages.created)  # type: ignore[attr-defined]
    assert "c9" in stages.deleted
    assert leads.moves and leads.moves[0][0] == "c9"
