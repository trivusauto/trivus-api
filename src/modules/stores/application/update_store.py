from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class UpdateStoreUseCase:
    def __init__(self, stores: StoreRepository, clone_template: object = None) -> None:
        self._stores = stores
        self._clone = clone_template

    async def execute(self, store_id: str, data: dict[str, object]) -> Store:
        before = await self._stores.get_by_id(store_id)
        updated = await self._stores.update(store_id, data)
        if self._clone is not None and data.get("crm_enabled") is True and (before is None or not before.crm_enabled):
            from src.modules.crm.application.clone_template import CloneTemplateUseCase
            clone: CloneTemplateUseCase = self._clone  # type: ignore[assignment]
            if not await clone.already_cloned(store_id):
                await clone.execute(store_id)
        return updated
