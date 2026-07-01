from src.modules.auth.domain.ports import StoreAccessReader


class GetAccessibleStoreIds:
    """
    Returns the list of store IDs accessible to the user, or None for admins (all stores).
    - admin → None (unrestricted)
    - shop_user → [parent_store_id]
    - client → ids from user_store_access (delegated to StoreAccessReader)
    """

    def __init__(self, reader: StoreAccessReader) -> None:
        self._reader = reader

    async def execute(self, user_id: str, role: str, parent_store_id: str | None) -> list[str] | None:
        if role == "admin":
            return None
        if role == "shop_user":
            return [parent_store_id] if parent_store_id else []
        # client
        return await self._reader.get_store_ids_for_user(user_id)
