from src.modules.auth.application.dto import AuthResult, LoginCommand
from src.modules.auth.domain.ports import PasswordHasher, TokenService, UserRepository
from src.shared.domain.errors import ForbiddenError, UnauthorizedError


class LoginUseCase:
    def __init__(self, users: UserRepository, hasher: PasswordHasher, tokens: TokenService) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, command: LoginCommand) -> AuthResult:
        user = await self._users.get_by_email(command.email.strip())
        if user is None:
            raise UnauthorizedError("Usuário ou senha inválidos")
        if not user.active:
            raise ForbiddenError("Acesso bloqueado. Seu usuário está inativo.")
        if not self._hasher.verify(command.password, user.password_hash):
            raise UnauthorizedError("Usuário ou senha inválidos")
        if self._hasher.needs_rehash(user.password_hash):
            await self._users.update_password(user.id, self._hasher.hash(command.password))
        token = self._tokens.issue({"sub": user.id, "role": user.role, "parent_store_id": user.parent_store_id})
        return AuthResult(access_token=token, user=user)
