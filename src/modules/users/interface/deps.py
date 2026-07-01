from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.stores.infrastructure.repository import SqlAlchemyUserStoreAccessRepository
from src.modules.users.application.assign_stores import AssignStoresUseCase
from src.modules.users.application.create_portal_user import CreatePortalUserUseCase
from src.modules.users.application.create_team_user import CreateTeamUserUseCase
from src.shared.infrastructure.database import get_session


def _users(session: AsyncSession = Depends(get_session)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def get_create_portal_uc(repo: SqlAlchemyUserRepository = Depends(_users)) -> CreatePortalUserUseCase:
    return CreatePortalUserUseCase(repo, Argon2PasswordHasher())


def get_create_team_uc(repo: SqlAlchemyUserRepository = Depends(_users)) -> CreateTeamUserUseCase:
    return CreateTeamUserUseCase(repo, Argon2PasswordHasher())


def get_assign_stores_uc(session: AsyncSession = Depends(get_session)) -> AssignStoresUseCase:
    return AssignStoresUseCase(SqlAlchemyUserStoreAccessRepository(session))


def get_user_repo(repo: SqlAlchemyUserRepository = Depends(_users)) -> SqlAlchemyUserRepository:
    return repo
