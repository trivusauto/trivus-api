from collections.abc import Awaitable, Callable

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.domain.errors import FeatureLockedError
from src.shared.infrastructure.database import get_session
from src.shared.interface.auth_deps import CurrentUser, get_current_user


def require_feature(feature_key: str) -> Callable[..., Awaitable[None]]:
    """Gate por feature key (rotas com store_id na query). Admin Trivus bypassa (E7);
    loja sem empresa vinculada não é gateada (E6, modo legado pré-ETL)."""

    async def checker(store_id: str = Query(...),
                      user: CurrentUser = Depends(get_current_user),
                      session: AsyncSession = Depends(get_session)) -> None:
        if user.role == "admin":                  # E7
            return
        from src.modules.ecosystem.infrastructure.entitlement_service import EntitlementService
        keys = await EntitlementService(session).feature_keys_for_store(store_id)
        if feature_key not in keys:
            raise FeatureLockedError(feature_key)

    return checker
