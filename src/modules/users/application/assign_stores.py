from src.modules.stores.domain.ports import UserStoreAccessRepository
from src.shared.domain.errors import DomainError


class AssignStoresUseCase:
    def __init__(self, access: UserStoreAccessRepository) -> None:
        self._access = access

    async def execute(self, user_id: str, store_ids: list[str], owner_store_ids: list[str]) -> None:
        unique = list(dict.fromkeys(s for s in store_ids if s))
        if not unique:
            raise DomainError("Selecione ao menos uma loja.")
        owners = set(owner_store_ids or unique)
        await self._access.replace_links(user_id, [(sid, sid in owners) for sid in unique])
