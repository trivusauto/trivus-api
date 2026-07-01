from src.modules.crm.infrastructure.repositories import CoolingRepository, FunnelRepository, StageRepository
from src.shared.domain.errors import NotFoundError


class CloneTemplateUseCase:
    def __init__(self, funnels: FunnelRepository, stages: StageRepository, cooling: CoolingRepository) -> None:
        self._funnels = funnels
        self._stages = stages
        self._cooling = cooling

    async def already_cloned(self, store_id: str) -> bool:
        return await self._funnels.first_clone(store_id) is not None

    async def execute(self, store_id: str) -> dict[str, object]:
        tpl = await self._funnels.first_template()
        if tpl is None:
            raise NotFoundError("Nenhum funil-template configurado.")
        clone = await self._funnels.create(store_id, tpl.name, 0, False, tpl.id)
        for ts in await self._stages.list_for_funnel(tpl.id):
            new_stage = await self._stages.create(clone.id, ts.name, ts.sort_order, ts.id)
            await self._cooling.copy(ts.id, new_stage.id)
        return {"id": str(clone.id), "name": tpl.name}
