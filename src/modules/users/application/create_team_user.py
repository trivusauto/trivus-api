from src.modules.auth.domain.entities import User
from src.modules.auth.domain.ports import PasswordHasher, UserRepository
from src.modules.users.application.dto import CreateTeamUserInput
from src.shared.domain.errors import DomainError


class CreateTeamUserUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(self, data: CreateTeamUserInput) -> User:
        # E-mail é UNIQUE no banco: sem esta checagem o insert estoura IntegrityError
        # e vira 500. Input inválido tem que voltar 4xx.
        if await self._users.get_by_email(data.email) is not None:
            raise DomainError(f"Já existe um usuário com o e-mail {data.email}.")
        return await self._users.create({
            "email": data.email, "name": data.name, "role": "shop_user",
            "password_hash": self._hasher.hash(data.password), "active": True,
            "parent_store_id": data.store_id, "shop_role": data.shop_role,
            "menu_permissions": data.menu_permissions,
            "can_see_unassigned_leads": data.can_see_unassigned_leads,
            "can_edit_others_leads": data.can_edit_others_leads,
        })
