from abc import ABC, abstractmethod
from src.modules.stores.domain.entities import Store


class StoreRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[Store]: ...
    @abstractmethod
    async def get_by_id(self, store_id: str) -> Store | None: ...
    @abstractmethod
    async def create(self, data: dict[str, object]) -> Store: ...
    @abstractmethod
    async def update(self, store_id: str, data: dict[str, object]) -> Store: ...
    @abstractmethod
    async def get_role_labels(self, store_id: str) -> object: ...
    @abstractmethod
    async def set_role_labels(self, store_id: str, labels: dict[str, str]) -> None: ...


class StoreAccessReader(ABC):
    @abstractmethod
    async def store_ids_for_user(self, user_id: str) -> list[str]: ...


class UserStoreAccessRepository(ABC):
    @abstractmethod
    async def replace_links(self, user_id: str, links: list[tuple[str, bool]]) -> None: ...
