from argon2 import PasswordHasher as Argon2
from argon2.exceptions import VerificationError, VerifyMismatchError
from src.modules.auth.domain.ports import PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self._ph = Argon2()

    def hash(self, password: str) -> str:
        return self._ph.hash(password)

    def verify(self, password: str, hashed: str | None) -> bool:
        if not hashed:
            return False
        if hashed.startswith("$argon2"):
            try:
                return self._ph.verify(hashed, password)
            except (VerifyMismatchError, VerificationError):
                return False
        # Hash legado do sistema antigo (spec §6.1).
        return hashed == f"hashed_{password}" or hashed == password

    def needs_rehash(self, hashed: str | None) -> bool:
        return not hashed or not hashed.startswith("$argon2")
