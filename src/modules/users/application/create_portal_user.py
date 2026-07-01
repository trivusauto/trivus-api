from src.modules.auth.domain.entities import User
from src.modules.auth.domain.ports import PasswordHasher, UserRepository


class CreatePortalUserUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, email: str, password: str, name: str | None) -> User:
        return await self._users.create({
            "email": email, "name": name, "role": "client",
            "password_hash": self._hasher.hash(password), "active": True,
        })
