from src.modules.crm.domain.stage_rules import StageRules
from src.modules.crm.infrastructure.repositories import ActivityRepository, HistoryRepository, LeadRepository, StageRepository
from src.modules.crm.infrastructure.store_flags import StoreFlagsReader
from src.shared.domain.errors import DomainError


def _is_receptivo(funil: object) -> bool:
    f = funil.strip() if isinstance(funil, str) else funil
    return (not f) or f == "receptivo"


class MoveLeadStageUseCase:
    def __init__(self, leads: LeadRepository, stages: StageRepository, history: HistoryRepository,
                 activity: ActivityRepository, rules: StageRules,
                 store_flags: StoreFlagsReader | None = None) -> None:
        self._leads = leads
        self._stages = stages
        self._history = history
        self._activity = activity
        self._rules = rules
        self._store_flags = store_flags

    async def execute(self, lead_id: str, to_stage_id: str, user: object) -> dict[str, object]:
        lead = await self._leads.get_or_raise(lead_id)
        target = await self._stages.get(to_stage_id)
        if target is None:
            raise DomainError("Etapa de destino inválida.")
        ordered = await self._stages.list_for_funnel(target.funnel_id)
        ids = [str(s.id) for s in ordered]
        from_i = ids.index(str(lead["stage_id"])) if str(lead["stage_id"]) in ids else -1
        to_i = ids.index(to_stage_id)
        if to_i > from_i:
            if (self._store_flags is not None and _is_receptivo(lead.get("funil"))
                    and not lead.get("campaign_id")
                    and await self._store_flags.require_campaign(str(lead["store_id"]))):
                raise DomainError("Preencha a campanha de marketing do lead antes de avançar.")
            stages_for_rules: list[dict[str, object]] = [{"name": s.name} for s in ordered]
            ok, missing = self._rules.can_advance(stages_for_rules, from_i, to_i, lead)
            if not ok:
                labels = ", ".join(dict.fromkeys(str(m["label"]) for m in missing))
                raise DomainError(f"Preencha os campos obrigatórios: {labels}.")
        moved = await self._leads.update(lead_id, {"stage_id": to_stage_id})
        await self._history.record(lead_id, to_stage_id)
        await self._activity.log(
            store_id=str(lead["store_id"]), actor_user_id=getattr(user, "user_id", None),
            action="lead_moved", entity_type="lead", entity_id=lead_id,
        )
        return moved
