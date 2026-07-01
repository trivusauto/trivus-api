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
    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def execute(self, store_id: str, user: object) -> list[dict[str, object]]:
        return await self._leads.list_for_board(store_id, user)


class DeleteLeadUseCase:
    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def execute(self, lead_id: str) -> None:
        await self._leads.delete(lead_id)
