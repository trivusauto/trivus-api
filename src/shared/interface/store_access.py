"""Guard de acesso à loja: impede que um usuário leia/escreva dados de uma
loja fora do seu escopo (isolamento multi-tenant).

admin  -> todas as lojas
shop_user -> apenas a própria (parent_store_id)
client -> apenas lojas vinculadas em user_store_access
"""
from fastapi import Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.modules.stores.infrastructure.orm import StoreModel
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


async def require_store_ids_access(
    store_ids: list[str] = Query(default=[]),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Dependência para rotas multi-loja (`?store_ids=a&store_ids=b`).

    Sem `store_ids` → todas as lojas acessíveis do usuário. Com `store_ids` → valida
    TODAS (qualquer uma fora do escopo derruba a requisição inteira com 403).
    Devolve a lista efetiva de lojas a consultar.
    """
    scope = await GetAccessibleStoreIdsUseCase(SqlAlchemyStoreAccessReader(session)).execute(user)

    if not store_ids:
        if scope is not None:
            return scope
        rows = (await session.execute(select(StoreModel.id).where(StoreModel.active.is_(True)))).scalars().all()
        return [str(r) for r in rows]

    if scope is not None:
        allowed = set(scope)
        if any(sid not in allowed for sid in store_ids):
            raise ForbiddenError("Loja fora do seu acesso.")
    return list(dict.fromkeys(store_ids))
