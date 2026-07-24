from src.modules.auth.domain.ports import UserRepository
from src.modules.crm.infrastructure.repositories import LeadRepository


class CreateLeadUseCase:
    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        return await self._leads.create(data)


class UpdateLeadUseCase:
    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def execute(self, lead_id: str, data: dict[str, object]) -> dict[str, object]:
        return await self._leads.update(lead_id, data)


class ListLeadsUseCase:
    def __init__(self, leads: LeadRepository, users: UserRepository | None = None) -> None:
        self._leads = leads
        self._users = users

    async def execute(
        self, store_id: str, user: object, assigned_to: str | None = None
    ) -> list[dict[str, object]]:
        """LEITURA LIBERADA (decisão do cliente 23/07): todo usuário com acesso à
        loja vê o quadro inteiro, independente do papel.

        A restrição passou a ser de ESCRITA, não de leitura — ver
        ``crm/application/edit_guard.py``. O param ``assigned_to`` segue como filtro
        opcional (o front usa no seletor "Responsável").

        ``can_see_unassigned_leads`` continua existindo para o round-robin do webhook.
        """
        return await self._leads.list_for_board(store_id, assigned_to=assigned_to)


class DeleteLeadUseCase:
    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def execute(self, lead_id: str) -> None:
        await self._leads.delete(lead_id)
