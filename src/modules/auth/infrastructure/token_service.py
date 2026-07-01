from datetime import datetime, timedelta, timezone
import jwt
from src.modules.auth.domain.ports import TokenService


class JwtTokenService(TokenService):
    def __init__(self, secret: str, expires_minutes: int) -> None:
        self._secret = secret
        self._expires_minutes = expires_minutes

    def issue(self, claims: dict[str, object]) -> str:
        payload = dict(claims)
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=self._expires_minutes)
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def verify(self, token: str) -> dict[str, object]:
        result: dict[str, object] = jwt.decode(token, self._secret, algorithms=["HS256"])
        return result
