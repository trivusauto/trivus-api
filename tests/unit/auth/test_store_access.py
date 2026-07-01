import pytest
from src.modules.auth.application.store_access import GetAccessibleStoreIds


class FakeReader:
    async def get_store_ids_for_user(self, user_id: str) -> list[str]:
        return ["store-a", "store-b"]


uc = GetAccessibleStoreIds(FakeReader())


@pytest.mark.asyncio
async def test_admin_returns_none() -> None:
    result = await uc.execute("u1", "admin", None)
    assert result is None


@pytest.mark.asyncio
async def test_shop_user_returns_own_store() -> None:
    result = await uc.execute("u2", "shop_user", "store-x")
    assert result == ["store-x"]


@pytest.mark.asyncio
async def test_shop_user_no_store_returns_empty() -> None:
    result = await uc.execute("u2", "shop_user", None)
    assert result == []


@pytest.mark.asyncio
async def test_client_delegates_to_reader() -> None:
    result = await uc.execute("u3", "client", None)
    assert result == ["store-a", "store-b"]
