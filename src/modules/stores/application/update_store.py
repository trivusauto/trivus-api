from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class UpdateStoreUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self, store_id: str, data: dict[str, object]) -> Store:
        return await self._stores.update(store_id, data)
