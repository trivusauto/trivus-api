from src.modules.stores.domain.ports import StoreAccessReader
from src.shared.interface.auth_deps import CurrentUser


class GetAccessibleStoreIdsUseCase:
    def __init__(self, reader: StoreAccessReader) -> None:
        self._reader = reader

    async def execute(self, user: CurrentUser) -> list[str] | None:
        """None = admin (todas as lojas)."""
        if user.role == "admin":
            return None
        if user.role == "shop_user" and user.parent_store_id:
            return [user.parent_store_id]
        return await self._reader.store_ids_for_user(user.user_id)
