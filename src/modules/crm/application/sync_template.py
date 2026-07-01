from src.modules.crm.infrastructure.orm import FunnelModel, StageModel
from src.modules.crm.infrastructure.repositories import CoolingRepository, FunnelRepository, LeadRepository, StageRepository


class SyncTemplateToClientsUseCase:
    def __init__(self, funnels: FunnelRepository, stages: StageRepository, cooling: CoolingRepository, leads: LeadRepository) -> None:
        self._funnels = funnels
        self._stages = stages
        self._cooling = cooling
        self._leads = leads

    async def execute(self, template_id: str) -> None:
        for clone in await self._funnels.list_clones(template_id):
            await self._sync_one(clone)

    async def _backfill_template_ids(self, tpl_stages: list[StageModel], client_stages: list[StageModel]) -> None:
        sorted_tpl = sorted(tpl_stages, key=lambda s: s.sort_order or 0)
        sorted_client = sorted(client_stages, key=lambda s: s.sort_order or 0)
        claimed = {str(s.template_stage_id) for s in client_stages if s.template_stage_id}
        for i, cs in enumerate(sorted_client):
            if cs.template_stage_id and str(cs.template_stage_id) in claimed:
                continue
            if i >= len(sorted_tpl):
                break
            ts = sorted_tpl[i]
            if str(ts.id) in claimed:
                continue
            await self._stages.update(cs.id, template_stage_id=str(ts.id))
            claimed.add(str(ts.id))

    async def _sync_one(self, clone: FunnelModel) -> None:
        if clone.template_source_id is None:
            return
        tpl = await self._funnels.get(clone.template_source_id)
        if tpl is None:
            return
        await self._funnels.update_name(clone.id, tpl.name)

        tpl_stages = await self._stages.list_for_funnel(tpl.id)
        client_stages = await self._stages.list_for_funnel(clone.id)
        # Only backfill for legacy clones where no stage has template_stage_id yet
        if not any(cs.template_stage_id for cs in client_stages):
            await self._backfill_template_ids(tpl_stages, client_stages)

        client_stages = await self._stages.list_for_funnel(clone.id)
        tpl_stage_ids = {str(s.id) for s in tpl_stages}
        by_template_id = {str(cs.template_stage_id): cs for cs in client_stages if cs.template_stage_id}

        first_client_stage_id: str | None = None
        for ts in tpl_stages:
            existing = by_template_id.get(str(ts.id))
            if existing is not None:
                await self._stages.update(existing.id, name=ts.name, sort_order=ts.sort_order)
                await self._cooling.copy(ts.id, existing.id)
                if first_client_stage_id is None:
                    first_client_stage_id = existing.id
            else:
                new_stage = await self._stages.create(clone.id, ts.name, ts.sort_order, str(ts.id))
                await self._cooling.copy(ts.id, new_stage.id)
                if first_client_stage_id is None:
                    first_client_stage_id = new_stage.id

        client_stages = await self._stages.list_for_funnel(clone.id)
        fallback = first_client_stage_id
        if fallback is None:
            fallback = next((s.id for s in client_stages if s.template_stage_id and str(s.template_stage_id) in tpl_stage_ids), None)
        if fallback is None and client_stages:
            fallback = client_stages[0].id

        orphans = [cs for cs in client_stages if not cs.template_stage_id or str(cs.template_stage_id) not in tpl_stage_ids]
        for orphan in orphans:
            if fallback and orphan.id != fallback:
                await self._leads.move_all_from_stage(orphan.id, fallback)
            await self._cooling.delete_for_stage(orphan.id)
            await self._stages.delete(orphan.id)
