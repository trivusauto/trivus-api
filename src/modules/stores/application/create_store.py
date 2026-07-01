from src.modules.stores.application.dto import CreateStoreInput
from src.modules.stores.domain.entities import Store
from src.modules.stores.domain.ports import StoreRepository


class CreateStoreUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self, data: CreateStoreInput) -> Store:
        payload: dict[str, object] = {"nome_fantasia": data.nome_fantasia, **data.fields}
        return await self._stores.create(payload)
