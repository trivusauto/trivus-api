from src.modules.crm.infrastructure.repositories import FunnelRepository, StageRepository


class ListFunnelsUseCase:
    def __init__(self, funnels: FunnelRepository, stages: StageRepository) -> None:
        self._funnels = funnels
        self._stages = stages

    async def execute(self, store_id: str) -> list[dict[str, object]]:
        out = []
        for f in await self._funnels.list_for_store(store_id):
            stage_rows = await self._stages.list_for_funnel(f.id)
            out.append({
                "id": str(f.id), "name": f.name, "sort_order": f.sort_order,
                "stages": [{"id": str(s.id), "name": s.name, "sort_order": s.sort_order} for s in stage_rows],
            })
        return out


class CreateStageUseCase:
    def __init__(self, stages: StageRepository) -> None:
        self._stages = stages

    async def execute(self, funnel_id: str, name: str, sort_order: int) -> dict[str, object]:
        s = await self._stages.create(funnel_id, name, sort_order)
        return {"id": str(s.id), "name": s.name, "sort_order": s.sort_order}


class RenameStageUseCase:
    def __init__(self, stages: StageRepository) -> None:
        self._stages = stages

    async def execute(self, stage_id: str, name: str) -> dict[str, object]:
        s = await self._stages.rename(stage_id, name)
        return {"id": str(s.id), "name": s.name, "sort_order": s.sort_order}
