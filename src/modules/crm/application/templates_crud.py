from src.modules.crm.infrastructure.repositories import FunnelRepository, StageRepository


class ListTemplatesUseCase:
    def __init__(self, funnels: FunnelRepository, stages: StageRepository) -> None:
        self._funnels = funnels
        self._stages = stages

    async def execute(self) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for f in await self._funnels.list_templates():
            stages = await self._stages.list_for_funnel(f.id)
            out.append({
                "id": str(f.id),
                "name": f.name,
                "sort_order": f.sort_order,
                "stages": [{"id": str(s.id), "name": s.name, "sort_order": s.sort_order} for s in stages],
            })
        return out


class CreateTemplateUseCase:
    def __init__(self, funnels: FunnelRepository, stages: StageRepository) -> None:
        self._funnels = funnels
        self._stages = stages

    async def execute(self, name: str, stage_names: list[str]) -> dict[str, object]:
        funnel = await self._funnels.create(None, name, 0, True, None)
        for i, sn in enumerate(stage_names):
            await self._stages.create(funnel.id, sn, i, None)
        return {"id": str(funnel.id), "name": name}
