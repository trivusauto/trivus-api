from collections.abc import Callable
from fastapi import Depends
from src.shared.domain.errors import ForbiddenError
from src.shared.interface.auth_deps import CurrentUser, get_current_user


def require_roles(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if roles and user.role not in roles:
            raise ForbiddenError("Acesso negado para o seu perfil.")
        return user
    return checker
