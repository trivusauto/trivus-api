from fastapi import APIRouter, Depends

from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.users.application.assign_stores import AssignStoresUseCase
from src.modules.users.application.create_portal_user import CreatePortalUserUseCase
from src.modules.users.application.create_team_user import CreateTeamUserUseCase
from src.modules.users.application.dto import CreateTeamUserInput
from src.modules.users.interface.deps import (
    get_assign_stores_uc,
    get_create_portal_uc,
    get_create_team_uc,
    get_user_repo,
)
from src.modules.users.interface.schemas import (
    AssignStoresRequest,
    CreatePortalUserRequest,
    CreateTeamUserRequest,
    PortalUserResponse,
)
from src.shared.interface.auth_deps import CurrentUser
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["users"])


@router.get("/admin/users")
async def list_portal(
    _: CurrentUser = Depends(require_roles("admin")),
    repo: SqlAlchemyUserRepository = Depends(get_user_repo),
) -> list[PortalUserResponse]:
    return [PortalUserResponse(id=u.id, email=u.email, name=u.name, role=u.role, active=u.active) for u in await repo.list_portal()]


@router.post("/admin/users", status_code=201)
async def create_portal(
    body: CreatePortalUserRequest,
    _: CurrentUser = Depends(require_roles("admin")),
    uc: CreatePortalUserUseCase = Depends(get_create_portal_uc),
) -> PortalUserResponse:
    u = await uc.execute(str(body.email), body.password, body.name)
    return PortalUserResponse(id=u.id, email=u.email, name=u.name, role=u.role, active=u.active)


@router.put("/admin/users/{user_id}/stores")
async def assign_stores(
    user_id: str,
    body: AssignStoresRequest,
    _: CurrentUser = Depends(require_roles("admin")),
    uc: AssignStoresUseCase = Depends(get_assign_stores_uc),
) -> dict[str, bool]:
    await uc.execute(user_id, body.store_ids, body.owner_store_ids)
    return {"ok": True}


@router.get("/stores/{store_id}/team")
async def list_team(
    store_id: str,
    _: CurrentUser = Depends(require_roles("admin", "client")),
    repo: SqlAlchemyUserRepository = Depends(get_user_repo),
) -> list[PortalUserResponse]:
    return [PortalUserResponse(id=u.id, email=u.email, name=u.name, role=u.role, active=u.active) for u in await repo.list_team(store_id)]


@router.post("/stores/{store_id}/team", status_code=201)
async def create_team(
    store_id: str,
    body: CreateTeamUserRequest,
    _: CurrentUser = Depends(require_roles("admin", "client")),
    uc: CreateTeamUserUseCase = Depends(get_create_team_uc),
) -> PortalUserResponse:
    data = CreateTeamUserInput(
        email=str(body.email), password=body.password, name=body.name, store_id=store_id,
        shop_role=body.shop_role, menu_permissions=body.menu_permissions,
        can_see_unassigned_leads=body.can_see_unassigned_leads,
    )
    u = await uc.execute(data)
    return PortalUserResponse(id=u.id, email=u.email, name=u.name, role=u.role, active=u.active)
