"""Guard de acesso à loja: impede que um usuário leia/escreva dados de uma
loja fora do seu escopo (isolamento multi-tenant).

admin  -> todas as lojas
shop_user -> apenas a própria (parent_store_id)
client -> apenas lojas vinculadas em user_store_access
"""
from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreAccessReader
from src.shared.domain.errors import ForbiddenError
from src.shared.infrastructure.database import get_session
from src.shared.interface.auth_deps import CurrentUser, get_current_user


async def assert_store_access(store_id: str, user: CurrentUser, session: AsyncSession) -> None:
    """Levanta ForbiddenError (403) se o usuário não tem acesso à loja."""
    scope = await GetAccessibleStoreIdsUseCase(SqlAlchemyStoreAccessReader(session)).execute(user)
    if scope is not None and store_id not in scope:
        raise ForbiddenError("Loja fora do seu acesso.")


async def require_store_access(
    store_id: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Dependência para rotas GET com store_id na query."""
    await assert_store_access(store_id, user, session)
