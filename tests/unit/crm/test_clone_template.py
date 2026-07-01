from src.modules.crm.application.clone_template import CloneTemplateUseCase


class FakeFunnels:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None

    async def first_template(self) -> object:
        return type("F", (), {"id": "tpl", "name": "Padrão"})()

    async def first_clone(self, store_id: str) -> object:
        return None

    async def create(self, store_id: str, name: str, sort_order: int = 0, is_template: bool = False, template_source_id: object = None) -> object:
        self.created = {"store_id": store_id, "name": name, "template_source_id": template_source_id}
        return type("F", (), {"id": "clone"})()


class FakeStages:
    async def list_for_funnel(self, fid: str) -> list[object]:
        return [type("S", (), {"id": "s1", "name": "RECEBIDOS", "sort_order": 0})()]

    async def create(self, funnel_id: str, name: str, sort_order: int = 0, template_stage_id: object = None) -> object:
        return type("S", (), {"id": "cs1"})()


class FakeCooling:
    async def list_for_stage(self, sid: str) -> list[object]:
        return []

    async def copy(self, src: str, dst: str) -> None:
        ...


async def test_clone_creates_funnel_and_stages() -> None:
    funnels = FakeFunnels()
    uc = CloneTemplateUseCase(funnels, FakeStages(), FakeCooling())
    out = await uc.execute("store-1")
    assert out["id"] == "clone"
    assert funnels.created is not None
    assert funnels.created["template_source_id"] == "tpl"
