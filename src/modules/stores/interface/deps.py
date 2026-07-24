from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.clone_template import CloneTemplateUseCase
from src.modules.crm.infrastructure.repositories import CoolingRepository, FunnelRepository, StageRepository
from src.modules.stores.application.create_store import CreateStoreUseCase
from src.modules.stores.application.list_stores import ListStoresUseCase
from src.modules.stores.application.role_labels import GetRoleLabelsUseCase, SetRoleLabelsUseCase
from src.modules.stores.application.update_store import UpdateStoreUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreRepository
from src.modules.users.application.create_team_user import CreateTeamUserUseCase
from src.modules.users.interface.deps import get_create_team_uc
from src.shared.infrastructure.database import get_session


def _repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemyStoreRepository:
    return SqlAlchemyStoreRepository(session)


def get_store_repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemyStoreRepository:
    return SqlAlchemyStoreRepository(session)


def get_list_stores_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> ListStoresUseCase:
    return ListStoresUseCase(repo)


def get_create_store_uc(
    repo: SqlAlchemyStoreRepository = Depends(_repo),
    team: CreateTeamUserUseCase = Depends(get_create_team_uc),
) -> CreateStoreUseCase:
    return CreateStoreUseCase(repo, team)


def get_update_store_uc(
    repo: SqlAlchemyStoreRepository = Depends(_repo),
    session: AsyncSession = Depends(get_session),
) -> UpdateStoreUseCase:
    clone = CloneTemplateUseCase(FunnelRepository(session), StageRepository(session), CoolingRepository(session))
    return UpdateStoreUseCase(repo, clone)


def get_role_labels_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> GetRoleLabelsUseCase:
    return GetRoleLabelsUseCase(repo)


def set_role_labels_uc(repo: SqlAlchemyStoreRepository = Depends(_repo)) -> SetRoleLabelsUseCase:
    return SetRoleLabelsUseCase(repo)
