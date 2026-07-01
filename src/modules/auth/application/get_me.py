from src.modules.auth.domain.entities import User
from src.modules.auth.domain.ports import UserRepository
from src.shared.domain.errors import NotFoundError


class GetMeUseCase:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, user_id: str) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        return user
