from fastapi import APIRouter, Depends, Query
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.metrics.application.dashboard import DashboardUseCase
from src.modules.metrics.application.projections import ProjectionsUseCase
from src.modules.metrics.application.reports import ReportUseCase
from src.modules.metrics.domain.team import build_team_performance
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.metrics.interface.deps import (
    get_accessible_uc, get_dashboard_uc, get_indicators_report_uc,
    get_projections_uc, get_report_uc, get_store_repo, get_user_repo,
)
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreRepository
from src.shared.domain.errors import DomainError
from src.shared.infrastructure.database import get_session
from src.shared.interface.auth_deps import CurrentUser, get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/metrics", tags=["metrics"])


async def _resolve(
    user: CurrentUser,
    store_id: str | None,
    access: GetAccessibleStoreIdsUseCase,
    stores: SqlAlchemyStoreRepository,
) -> list[str]:
    scope = await access.execute(user)
    if store_id:
        if scope is not None and store_id not in scope:
            raise DomainError("Loja fora do escopo.")
        return [store_id]
    if scope is None:
        return [s.id for s in await stores.list_all()]
    return scope


@router.get("/dashboard")
async def dashboard(
    store_id: str | None = Query(None),
    start: str = Query(...),
    end: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
    uc: DashboardUseCase = Depends(get_dashboard_uc),
    access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc),
    stores: SqlAlchemyStoreRepository = Depends(get_store_repo),
) -> dict[str, object]:
    return await uc.execute(await _resolve(user, store_id, access, stores), start, end)


@router.get("/reports")
async def reports(
    store_id: str | None = Query(None),
    start: str = Query(...),
    end: str = Query(...),
    campaign_id: str | None = Query(None),
    user: CurrentUser = Depends(get_current_user),
    uc: ReportUseCase = Depends(get_report_uc),
    access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc),
    stores: SqlAlchemyStoreRepository = Depends(get_store_repo),
) -> dict[str, object]:
    return await uc.execute(await _resolve(user, store_id, access, stores), start, end, campaign_id)


@router.get("/projections")
async def projections(
    year: int = Query(...),
    month: int = Query(...),
    store_id: str | None = Query(None),
    user: CurrentUser = Depends(get_current_user),
    uc: ProjectionsUseCase = Depends(get_projections_uc),
    access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc),
    stores: SqlAlchemyStoreRepository = Depends(get_store_repo),
) -> dict[str, object]:
    return await uc.execute(await _resolve(user, store_id, access, stores), year, month)


@router.get("/indicators-report")
async def indicators_report(
    store_id: str = Query(...),
    date_from: str = Query(..., alias="from"),
    date_to: str = Query(..., alias="to"),
    year: int = Query(...),
    month: int = Query(...),
    user: CurrentUser = Depends(get_current_user),
    access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc),
    uc: object = Depends(get_indicators_report_uc),
) -> dict[str, object]:
    scope = await access.execute(user)
    if scope is not None and store_id not in scope:
        raise DomainError("Loja fora do escopo.")
    from src.modules.metrics.application.indicators_report import IndicatorsReportUseCase
    assert isinstance(uc, IndicatorsReportUseCase)
    return await uc.execute(store_id, date_from, date_to, year, month)


@router.get("/team")
async def team(
    store_id: str = Query(...),
    start: str = Query(...),
    end: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
    access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc),
    user_repo: SqlAlchemyUserRepository = Depends(get_user_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    scope = await access.execute(user)
    if scope is not None and store_id not in scope:
        raise DomainError("Loja fora do escopo.")
    team_users_domain = await user_repo.list_team(store_id)
    team_users: list[dict[str, object]] = [
        {"id": u.id, "name": u.name, "shop_role": u.shop_role} for u in team_users_domain
    ]
    reader = MetricsLeadReader(session)
    leads = await reader.leads_for_stores([store_id])
    return build_team_performance(leads, team_users, start, end)
