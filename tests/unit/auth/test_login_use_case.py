import pytest
from src.modules.auth.application.dto import LoginCommand
from src.modules.auth.application.login import LoginUseCase
from src.modules.auth.domain.entities import User
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.shared.domain.errors import ForbiddenError, UnauthorizedError


class FakeUserRepo:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.updated_password: str | None = None

    async def get_by_email(self, email: str) -> User | None:
        return self.user

    async def get_by_id(self, user_id: str) -> User | None:
        return self.user

    async def update_password(self, user_id: str, password_hash: str) -> None:
        self.updated_password = password_hash


class FakeToken:
    def issue(self, claims: dict[str, object]) -> str:
        return "token-123"

    def verify(self, token: str) -> dict[str, object]:
        return {}


@pytest.mark.asyncio
async def test_unknown_email() -> None:
    uc = LoginUseCase(FakeUserRepo(None), Argon2PasswordHasher(), FakeToken())
    with pytest.raises(UnauthorizedError):
        await uc.execute(LoginCommand(email="x@y.com", password="p"))


@pytest.mark.asyncio
async def test_inactive_user() -> None:
    user = User(id="1", email="a@b.com", name="A", role="admin", parent_store_id=None, active=False, password_hash="hashed_p")
    uc = LoginUseCase(FakeUserRepo(user), Argon2PasswordHasher(), FakeToken())
    with pytest.raises(ForbiddenError):
        await uc.execute(LoginCommand(email="a@b.com", password="p"))


@pytest.mark.asyncio
async def test_login_ok_and_rehash() -> None:
    user = User(id="1", email="a@b.com", name="A", role="admin", parent_store_id=None, active=True, password_hash="hashed_p")
    repo = FakeUserRepo(user)
    uc = LoginUseCase(repo, Argon2PasswordHasher(), FakeToken())
    result = await uc.execute(LoginCommand(email="a@b.com", password="p"))
    assert result.access_token == "token-123"
    assert result.user.id == "1"
    assert repo.updated_password is not None and repo.updated_password.startswith("$argon2")
