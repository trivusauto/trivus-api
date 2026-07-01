from src.modules.crm.domain.lead_patch import LeadPatch
from src.modules.crm.infrastructure.repositories import LeadRepository


class SetAgendamentoUseCase:
    def __init__(self, leads: LeadRepository, patch: LeadPatch) -> None:
        self._leads = leads
        self._patch = patch

    async def execute(self, lead_id: str, data_agendamento: str | None, hora_agendamento: str | None, user: object) -> dict[str, object]:
        prev = await self._leads.get_or_raise(lead_id)
        return await self._leads.update(lead_id, self._patch.agendamento(prev, data_agendamento, hora_agendamento, getattr(user, "user_id", None)))


class SetCompareceuUseCase:
    def __init__(self, leads: LeadRepository, patch: LeadPatch) -> None:
        self._leads = leads
        self._patch = patch

    async def execute(self, lead_id: str, compareceu: bool) -> dict[str, object]:
        prev = await self._leads.get_or_raise(lead_id)
        return await self._leads.update(lead_id, self._patch.compareceu(prev, compareceu))


class SetFechamentoUseCase:
    def __init__(self, leads: LeadRepository, patch: LeadPatch) -> None:
        self._leads = leads
        self._patch = patch

    async def execute(self, lead_id: str, receita: str | None, despesa: str | None, rentabilidade: str | None) -> dict[str, object]:
        prev = await self._leads.get_or_raise(lead_id)
        return await self._leads.update(lead_id, self._patch.fechamento(prev, receita, despesa, rentabilidade))
