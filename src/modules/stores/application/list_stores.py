from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class ListStoresUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self) -> list[Store]:
        return await self._stores.list_all()
