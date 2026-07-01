from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.auth.domain.entities import User
from src.modules.auth.domain.ports import UserRepository
from src.modules.auth.infrastructure.orm import UserModel


def _to_domain(row: UserModel) -> User:
    return User(
        id=str(row.id), email=row.email, name=row.name, role=row.role,
        parent_store_id=str(row.parent_store_id) if row.parent_store_id else None,
        active=row.active, password_hash=row.password_hash,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        row = (await self._session.execute(select(UserModel).where(UserModel.email == email))).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_by_id(self, user_id: str) -> User | None:
        row = await self._session.get(UserModel, user_id)
        return _to_domain(row) if row else None

    async def update_password(self, user_id: str, password_hash: str) -> None:
        row = await self._session.get(UserModel, user_id)
        if row:
            row.password_hash = password_hash
            await self._session.flush()
