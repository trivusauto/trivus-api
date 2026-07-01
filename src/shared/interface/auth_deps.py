from dataclasses import dataclass
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.modules.auth.interface.deps import get_token_service
from src.modules.auth.infrastructure.token_service import JwtTokenService
from src.shared.domain.errors import UnauthorizedError

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user_id: str
    role: str
    parent_store_id: str | None


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    tokens: JwtTokenService = Depends(get_token_service),
) -> CurrentUser:
    if cred is None:
        raise UnauthorizedError("Token ausente")
    try:
        claims = tokens.verify(cred.credentials)
    except Exception as exc:
        raise UnauthorizedError("Token inválido") from exc
    return CurrentUser(
        user_id=str(claims["sub"]),
        role=str(claims["role"]),
        parent_store_id=str(claims["parent_store_id"]) if claims.get("parent_store_id") else None,
    )
