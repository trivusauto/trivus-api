import uuid

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
        shop_role=row.shop_role, menu_permissions=[str(p) for p in (row.menu_permissions or [])],
        can_see_unassigned_leads=row.can_see_unassigned_leads,
        can_edit_others_leads=row.can_edit_others_leads,
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

    async def set_can_edit_others_leads(self, user_id: str, value: bool) -> User | None:
        """Concede/retira a autorização de editar leads de terceiros."""
        row = await self._session.get(UserModel, user_id)
        if not row:
            return None
        row.can_edit_others_leads = value
        await self._session.flush()
        return _to_domain(row)

    async def create(self, data: dict[str, object]) -> User:
        row = UserModel(id=str(uuid.uuid4()), **data)
        self._session.add(row)
        await self._session.flush()
        return _to_domain(row)

    async def list_portal(self) -> list[User]:
        stmt = select(UserModel).where(UserModel.role == "client", UserModel.parent_store_id.is_(None)).order_by(UserModel.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]

    async def list_team(self, store_id: str) -> list[User]:
        stmt = select(UserModel).where(UserModel.parent_store_id == store_id, UserModel.role == "shop_user").order_by(UserModel.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_domain(r) for r in rows]
