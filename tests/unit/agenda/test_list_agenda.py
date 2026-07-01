import pytest
from dataclasses import dataclass
from src.modules.agenda.application.list_agenda import ListAgendaUseCase


@dataclass
class Cur:
    user_id: str
    role: str
    parent_store_id: str | None = None


@dataclass
class DomainUser:
    shop_role: str | None
    can_see_unassigned_leads: bool


class FakeUsers:
    def __init__(self, u: DomainUser) -> None:
        self.u = u

    async def get_by_id(self, uid: str) -> DomainUser:
        return self.u


class FakeReader:
    def __init__(self) -> None:
        self.scope: dict[str, object] | None = None

    async def query(self, **kw: object) -> tuple[list[object], int]:
        self.scope = kw["scope"]  # type: ignore[assignment]
        return [], 0


@pytest.mark.asyncio
async def test_client_is_gestor() -> None:
    reader = FakeReader()
    uc = ListAgendaUseCase(reader, FakeUsers(DomainUser("vendedor", False)))  # type: ignore[arg-type]
    await uc.execute(Cur("u1", "client"), {"store_id": "s1"})
    assert reader.scope is not None
    assert reader.scope["gestor"] is True


@pytest.mark.asyncio
async def test_shop_user_non_gestor_scope() -> None:
    reader = FakeReader()
    uc = ListAgendaUseCase(reader, FakeUsers(DomainUser("vendedor", True)))  # type: ignore[arg-type]
    await uc.execute(Cur("u2", "shop_user", "s1"), {"store_id": "s1"})
    assert reader.scope is not None
    assert reader.scope["gestor"] is False
    assert reader.scope["user_id"] == "u2"
    assert reader.scope["include_unassigned"] is True


@pytest.mark.asyncio
async def test_gerente_is_gestor() -> None:
    reader = FakeReader()
    uc = ListAgendaUseCase(reader, FakeUsers(DomainUser("gerente", False)))  # type: ignore[arg-type]
    await uc.execute(Cur("u3", "shop_user", "s1"), {"store_id": "s1"})
    assert reader.scope is not None
    assert reader.scope["gestor"] is True
