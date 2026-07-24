import pytest
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.modules.auth.domain.entities import User
from src.modules.users.application.assign_stores import AssignStoresUseCase
from src.modules.users.application.create_team_user import CreateTeamUserUseCase
from src.modules.users.application.dto import CreateTeamUserInput
from src.shared.domain.errors import DomainError


class FakeUserRepo:
    def __init__(self, existing_email: str | None = None) -> None:
        self.created: dict[str, object] | None = None
        self._existing_email = existing_email

    async def get_by_email(self, email: str) -> User | None:
        if email != self._existing_email:
            return None
        return User(
            id="u0", email=email, name="Existente", role="shop_user",
            parent_store_id="s1", active=True, password_hash="x",
        )

    async def create(self, data: dict[str, object]) -> User:
        self.created = data
        return User(
            id="u1", email=str(data["email"]), name=str(data.get("name", "")), role=str(data["role"]),
            parent_store_id=str(data["parent_store_id"]) if data.get("parent_store_id") else None,
            active=True, password_hash=str(data["password_hash"]),
        )


class FakeAccessRepo:
    def __init__(self) -> None:
        self.links: tuple[str, list[tuple[str, bool]]] | None = None

    async def replace_links(self, user_id: str, links: list[tuple[str, bool]]) -> None:
        self.links = (user_id, links)


async def test_create_team_user_hashes_password() -> None:
    repo = FakeUserRepo()
    uc = CreateTeamUserUseCase(repo, Argon2PasswordHasher())  # type: ignore[arg-type]
    out = await uc.execute(CreateTeamUserInput(
        email="c@l.com", password="segredo1", name="Colab", store_id="s1",
        shop_role="sdr", menu_permissions=["/crm"], can_see_unassigned_leads=True,
    ))
    assert out.role == "shop_user"
    assert repo.created is not None
    assert str(repo.created["password_hash"]).startswith("$argon2")
    assert repo.created["parent_store_id"] == "s1"
    assert repo.created["can_see_unassigned_leads"] is True


async def test_assign_stores_replaces_links() -> None:
    repo = FakeAccessRepo()
    await AssignStoresUseCase(repo).execute("u1", ["a", "b"], ["a"])  # type: ignore[arg-type]
    assert repo.links == ("u1", [("a", True), ("b", False)])


async def test_assign_stores_requires_one() -> None:
    with pytest.raises(DomainError):
        await AssignStoresUseCase(FakeAccessRepo()).execute("u1", [], [])  # type: ignore[arg-type]


async def test_create_team_user_recusa_email_duplicado() -> None:
    """E-mail já usado vira DomainError (4xx), não IntegrityError (500)."""
    repo = FakeUserRepo(existing_email="ja@existe.com")
    uc = CreateTeamUserUseCase(repo, Argon2PasswordHasher())  # type: ignore[arg-type]
    with pytest.raises(DomainError):
        await uc.execute(CreateTeamUserInput(
            email="ja@existe.com", password="segredo1", name="Dup", store_id="s1",
        ))
    assert repo.created is None
