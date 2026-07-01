from src.modules.auth.domain.ports import PasswordHasher, UserRepository
from src.shared.domain.errors import NotFoundError, UnauthorizedError


class ChangePasswordUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, user_id: str, current_password: str, new_password: str) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        if not self._hasher.verify(current_password, user.password_hash):
            raise UnauthorizedError("Senha atual incorreta")
        await self._users.update_password(user_id, self._hasher.hash(new_password))
