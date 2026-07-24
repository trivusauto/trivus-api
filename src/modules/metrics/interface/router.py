from fastapi import APIRouter, Depends, Query
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.metrics.application.dashboard import DashboardUseCase
from src.modules.metrics.application.projections import ProjectionsUseCase
from src.modules.metrics.application.reports import ReportUseCase
from src.modules.metrics.domain.team import build_team_performance
from src.modules.metrics.infrastructure.marketing_series_reader import (
    MarketingSeriesReader, previous_window, totals_of,
)
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.metrics.interface.deps import (
    get_accessible_uc, get_dashboard_uc, get_indicators_report_uc,
    get_projections_uc, get_report_uc, get_store_repo, get_user_repo,
)
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreRepository
from src.shared.domain.errors import DomainError
from src.shared.infrastructure.database import get_session
from src.shared.interface.feature_gate import require_feature
from src.shared.interface.auth_deps import CurrentUser, get_current_user
from src.shared.interface.store_access import require_store_access, require_store_ids_access
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
    store_ids: list[str] = Query(default=[]),
    start: str = Query(...),
    end: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
    uc: DashboardUseCase = Depends(get_dashboard_uc),
    access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc),
    stores: SqlAlchemyStoreRepository = Depends(get_store_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    # Sem store_ids a resposta é a de sempre ({totals, monthly}) — compat.
    if not store_ids:
        return await uc.execute(await _resolve(user, store_id, access, stores), start, end)

    effective = await require_store_ids_access(store_ids=store_ids, user=user, session=session)
    names = {s.id: s.nome_fantasia for s in await stores.list_all()}
    return await uc.execute_multi(effective, start, end, names)


@router.get(
    "/marketing/series",
    dependencies=[Depends(require_feature("metrics.marketing")), Depends(require_store_access)],
)
async def marketing_series(
    store_id: str = Query(...),
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Série diária + total do período + total da janela anterior (S4.4)."""
    reader = MarketingSeriesReader(session)
    days = await reader.days([store_id], from_, to)
    prev_from, prev_to = previous_window(from_, to)
    previous_days = await reader.days([store_id], prev_from, prev_to)
    return {
        "days": days,
        "totals": totals_of(days),
        "previous_totals": totals_of(previous_days),
        "previous_range": {"from": prev_from, "to": prev_to},
    }


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
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    result = await uc.execute(await _resolve(user, store_id, access, stores), start, end, campaign_id)
    if user.role != "admin" and store_id:
        # E4: response-shaping — sem a key de custos, o dado nem sai da API
        from src.modules.ecosystem.infrastructure.entitlement_service import EntitlementService
        keys = await EntitlementService(session).feature_keys_for_store(store_id)
        if "metrics.reports.costs" not in keys:
            result["costs"] = None
            result["investment"] = None
    return result


@router.get("/projections")
async def projections(
    year: int = Query(...),
    month: int = Query(...),
    store_id: str | None = Query(None),
    store_ids: list[str] = Query(default=[]),
    user_id: str | None = Query(None),
    user: CurrentUser = Depends(get_current_user),
    uc: ProjectionsUseCase = Depends(get_projections_uc),
    access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc),
    stores: SqlAlchemyStoreRepository = Depends(get_store_repo),
    users: SqlAlchemyUserRepository = Depends(get_user_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    if not 1 <= month <= 12:
        raise DomainError("Mês inválido (use 1-12).")

    if store_ids:
        effective_stores = await require_store_ids_access(store_ids=store_ids, user=user, session=session)
    else:
        effective_stores = await _resolve(user, store_id, access, stores)

    # ESCOPO IMPOSTO NO BACKEND: shop_user comum só enxerga os próprios números,
    # mesmo que mande o id de outra pessoa. Gerente/dono/admin escolhem livremente.
    scoped_user = user_id
    if user.role == "shop_user":
        me = await users.get_by_id(user.user_id)
        if not (me and me.shop_role == "gerente"):
            scoped_user = user.user_id

    return await uc.execute(effective_stores, year, month, scoped_user)


@router.get("/indicators-report", dependencies=[Depends(require_feature("indicators"))])
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


@router.get("/team", dependencies=[Depends(require_feature("metrics.team"))])
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
