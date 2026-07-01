from src.modules.stores.domain.ports import StoreRepository
from src.modules.stores.domain.role_labels import merge_shop_role_labels


class GetRoleLabelsUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self, store_id: str) -> dict[str, str]:
        return merge_shop_role_labels(await self._stores.get_role_labels(store_id))


class SetRoleLabelsUseCase:
    def __init__(self, stores: StoreRepository) -> None:
        self._stores = stores

    async def execute(self, store_id: str, labels: dict[str, str]) -> dict[str, str]:
        merged = merge_shop_role_labels(labels)
        await self._stores.set_role_labels(store_id, merged)
        return merged
