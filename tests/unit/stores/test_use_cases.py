import pytest
from src.modules.stores.application.create_store import CreateStoreUseCase
from src.modules.stores.application.dto import CreateStoreInput
from src.modules.stores.application.update_store import UpdateStoreUseCase
from src.modules.stores.domain.entities import Store
from src.shared.domain.errors import NotFoundError


class FakeStoreRepo:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None
        self.store: Store | None = None

    async def list_all(self) -> list[Store]:
        return []

    async def get_by_id(self, sid: str) -> Store | None:
        return self.store

    async def create(self, data: dict[str, object]) -> Store:
        self.created = data
        return Store(id="new", nome_fantasia=str(data["nome_fantasia"]))

    async def update(self, sid: str, data: dict[str, object]) -> Store:
        if self.store is None:
            raise NotFoundError("x")
        return Store(id=sid, nome_fantasia="x", crm_enabled=bool(data.get("crm_enabled")))

    async def get_role_labels(self, sid: str) -> object:
        return None

    async def set_role_labels(self, sid: str, labels: dict[str, str]) -> None:
        ...


async def test_create_store() -> None:
    repo = FakeStoreRepo()
    out = await CreateStoreUseCase(repo).execute(CreateStoreInput(nome_fantasia="Auto X", fields={"cnpj": "123"}))
    assert out.id == "new"
    assert repo.created == {"nome_fantasia": "Auto X", "cnpj": "123"}


async def test_update_missing_store_raises() -> None:
    repo = FakeStoreRepo()
    with pytest.raises(NotFoundError):
        await UpdateStoreUseCase(repo).execute("missing", {"crm_enabled": True})
