from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.stores.application.create_store import CreateStoreUseCase
from src.modules.stores.application.list_stores import ListStoresUseCase
from src.modules.stores.application.update_store import UpdateStoreUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreRepository
from src.shared.infrastructure.database import get_session


def _repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemyStoreRepository:
    return SqlAlchemyStoreRepository(session)


def get_list_stores_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> ListStoresUseCase:
    return ListStoresUseCase(repo)


def get_create_store_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> CreateStoreUseCase:
    return CreateStoreUseCase(repo)


def get_update_store_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> UpdateStoreUseCase:
    return UpdateStoreUseCase(repo)
