from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.auth.application.get_me import GetMeUseCase
from src.modules.auth.application.login import LoginUseCase
from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.auth.infrastructure.token_service import JwtTokenService
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.settings import get_settings


def get_token_service() -> JwtTokenService:
    s = get_settings()
    return JwtTokenService(secret=s.jwt_secret, expires_minutes=s.jwt_expires_minutes)


def get_login_use_case(session: AsyncSession = Depends(get_session)) -> LoginUseCase:
    return LoginUseCase(SqlAlchemyUserRepository(session), Argon2PasswordHasher(), get_token_service())


def get_me_use_case(session: AsyncSession = Depends(get_session)) -> GetMeUseCase:
    return GetMeUseCase(SqlAlchemyUserRepository(session))
