from abc import ABC, abstractmethod
from src.modules.auth.domain.entities import User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...
    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...
    @abstractmethod
    async def update_password(self, user_id: str, password_hash: str) -> None: ...


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...
    @abstractmethod
    def verify(self, password: str, hashed: str | None) -> bool: ...
    @abstractmethod
    def needs_rehash(self, hashed: str | None) -> bool: ...


class TokenService(ABC):
    @abstractmethod
    def issue(self, claims: dict[str, object]) -> str: ...
    @abstractmethod
    def verify(self, token: str) -> dict[str, object]: ...


class StoreAccessReader(ABC):
    @abstractmethod
    async def get_store_ids_for_user(self, user_id: str) -> list[str]: ...
