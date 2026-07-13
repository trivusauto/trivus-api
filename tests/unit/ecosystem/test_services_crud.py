import pytest

from src.modules.ecosystem.application.services_crud import (
    CreateServiceUseCase, DeactivateServiceUseCase, UpdateServiceUseCase,
)
from src.shared.domain.errors import DomainError


class FakeServices:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None
        self.updated: dict[str, object] | None = None
        self.existing: dict[str, object] | None = None

    async def get_by_key(self, key: str) -> dict[str, object] | None:
        return self.existing

    async def get_or_raise(self, sid: str) -> dict[str, object]:
        return {"id": sid, "key": "crm_completo", "active": True}

    async def create(self, data: dict[str, object]) -> dict[str, object]:
        self.created = data
        return {"id": "s1", **data}

    async def update(self, sid: str, data: dict[str, object]) -> dict[str, object]:
        self.updated = data
        return {"id": sid, **data}


class FakePlans:
    def __init__(self, using: bool = False) -> None:
        self.using = using

    async def list_all(self) -> list[dict[str, object]]:
        return [{"id": "p1", "key": "pro", "service_keys": ["crm_completo"] if self.using else []}]


@pytest.mark.asyncio
async def test_create_validates_feature_keys() -> None:
    uc = CreateServiceUseCase(FakeServices())
    with pytest.raises(DomainError, match="feature key"):
        await uc.execute({"key": "x", "name": "X", "type": "software", "feature_keys": ["nao.existe"]})


@pytest.mark.asyncio
async def test_create_rejects_duplicate_key() -> None:
    repo = FakeServices()
    repo.existing = {"id": "s0", "key": "crm_completo"}
    with pytest.raises(DomainError, match="key"):
        await CreateServiceUseCase(repo).execute(
            {"key": "crm_completo", "name": "X", "type": "software", "feature_keys": []})


@pytest.mark.asyncio
async def test_update_cannot_change_key() -> None:
    repo = FakeServices()
    await UpdateServiceUseCase(repo).execute("s1", {"key": "outra", "name": "Novo nome"})
    assert repo.updated is not None and "key" not in repo.updated   # key imutável


@pytest.mark.asyncio
async def test_deactivate_blocked_when_in_plan() -> None:
    uc = DeactivateServiceUseCase(FakeServices(), FakePlans(using=True))
    with pytest.raises(DomainError, match="plano"):
        await uc.execute("s1")


@pytest.mark.asyncio
async def test_deactivate_ok_when_unused() -> None:
    repo = FakeServices()
    res = await DeactivateServiceUseCase(repo, FakePlans(using=False)).execute("s1")
    assert res["active"] is False
