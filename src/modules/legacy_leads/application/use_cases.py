from src.modules.legacy_leads.infrastructure.repository import LegacyLeadRepository


class ListLegacyLeadsUseCase:
    def __init__(self, repo: LegacyLeadRepository) -> None:
        self._repo = repo

    async def execute(self, store_id: str) -> list[dict[str, object]]:
        return await self._repo.list_for_store(store_id)


class CreateLegacyLeadUseCase:
    def __init__(self, repo: LegacyLeadRepository) -> None:
        self._repo = repo

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        return await self._repo.create(data)


class UpdateLegacyLeadUseCase:
    def __init__(self, repo: LegacyLeadRepository) -> None:
        self._repo = repo

    async def execute(self, lead_id: str, data: dict[str, object]) -> dict[str, object]:
        return await self._repo.update(lead_id, data)


class DeleteLegacyLeadUseCase:
    def __init__(self, repo: LegacyLeadRepository) -> None:
        self._repo = repo

    async def execute(self, lead_id: str) -> None:
        await self._repo.delete(lead_id)
