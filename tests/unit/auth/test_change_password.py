import pytest
from src.modules.auth.application.change_password import ChangePasswordUseCase
from src.modules.auth.domain.entities import User
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.shared.domain.errors import NotFoundError, UnauthorizedError


class FakeRepo:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.updated_hash: str | None = None

    async def get_by_email(self, email: str) -> User | None:
        return self.user

    async def get_by_id(self, user_id: str) -> User | None:
        return self.user

    async def update_password(self, user_id: str, password_hash: str) -> None:
        self.updated_hash = password_hash


h = Argon2PasswordHasher()


@pytest.mark.asyncio
async def test_user_not_found() -> None:
    uc = ChangePasswordUseCase(FakeRepo(None), h)
    with pytest.raises(NotFoundError):
        await uc.execute("u1", "old", "new")


@pytest.mark.asyncio
async def test_wrong_current_password() -> None:
    user = User(id="u1", email="a@b.com", name=None, role="admin", parent_store_id=None, active=True, password_hash="hashed_correct")
    uc = ChangePasswordUseCase(FakeRepo(user), h)
    with pytest.raises(UnauthorizedError):
        await uc.execute("u1", "wrong", "new")


@pytest.mark.asyncio
async def test_change_password_ok() -> None:
    user = User(id="u1", email="a@b.com", name=None, role="admin", parent_store_id=None, active=True, password_hash="hashed_old")
    repo = FakeRepo(user)
    uc = ChangePasswordUseCase(repo, h)
    await uc.execute("u1", "old", "newsecret")
    assert repo.updated_hash is not None
    assert repo.updated_hash.startswith("$argon2")
