from dataclasses import dataclass

from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase


@dataclass
class U:
    user_id: str
    role: str
    parent_store_id: str | None


class FakeReader:
    def __init__(self, ids: list[str]) -> None:
        self.ids = ids

    async def store_ids_for_user(self, user_id: str) -> list[str]:
        return self.ids


async def test_admin_none() -> None:
    uc = GetAccessibleStoreIdsUseCase(FakeReader([]))  # type: ignore[arg-type]
    assert await uc.execute(U("1", "admin", None)) is None  # type: ignore[arg-type]


async def test_shop_user_parent_only() -> None:
    uc = GetAccessibleStoreIdsUseCase(FakeReader([]))  # type: ignore[arg-type]
    assert await uc.execute(U("2", "shop_user", "store-9")) == ["store-9"]  # type: ignore[arg-type]


async def test_client_from_access() -> None:
    uc = GetAccessibleStoreIdsUseCase(FakeReader(["a", "b"]))  # type: ignore[arg-type]
    assert await uc.execute(U("3", "client", None)) == ["a", "b"]  # type: ignore[arg-type]
