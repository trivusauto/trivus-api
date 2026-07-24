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
    UpdateTeamUserRequest,
)
from src.shared.domain.errors import ForbiddenError, NotFoundError
from src.shared.interface.auth_deps import CurrentUser, get_current_user
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["users"])


async def require_team_access(
    store_id: str,
    user: CurrentUser = Depends(get_current_user),
    repo: SqlAlchemyUserRepository = Depends(get_user_repo),
) -> CurrentUser:
    """Acesso à equipe da loja (ler e escrever): admin/dono sempre; gerente
    apenas na própria loja. Qualquer outro caso → 403."""
    if user.role in ("admin", "client"):
        return user
    if user.role == "shop_user":
        u = await repo.get_by_id(user.user_id)
        if u and u.shop_role == "gerente" and str(u.parent_store_id) == store_id:
            return user
    raise ForbiddenError("Acesso negado para o seu perfil.")


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
    _: CurrentUser = Depends(require_team_access),
    repo: SqlAlchemyUserRepository = Depends(get_user_repo),
) -> list[PortalUserResponse]:
    return [
        PortalUserResponse(
            id=u.id, email=u.email, name=u.name, role=u.role, active=u.active,
            shop_role=u.shop_role, can_edit_others_leads=u.can_edit_others_leads,
        )
        for u in await repo.list_team(store_id)
    ]


@router.patch("/stores/{store_id}/team/{user_id}")
async def update_team_member(
    store_id: str,
    user_id: str,
    body: UpdateTeamUserRequest,
    _: CurrentUser = Depends(require_team_access),
    repo: SqlAlchemyUserRepository = Depends(get_user_repo),
) -> PortalUserResponse:
    """Concede/retira a flag de edição. O alvo precisa ser da MESMA loja do path."""
    target = await repo.get_by_id(user_id)
    if not target or target.parent_store_id != store_id:
        raise NotFoundError("Colaborador não encontrado nesta loja.")
    u = await repo.set_can_edit_others_leads(user_id, body.can_edit_others_leads)
    if not u:
        raise NotFoundError("Colaborador não encontrado nesta loja.")
    return PortalUserResponse(
        id=u.id, email=u.email, name=u.name, role=u.role, active=u.active,
        shop_role=u.shop_role, can_edit_others_leads=u.can_edit_others_leads,
    )


@router.post("/stores/{store_id}/team", status_code=201)
async def create_team(
    store_id: str,
    body: CreateTeamUserRequest,
    _: CurrentUser = Depends(require_team_access),
    uc: CreateTeamUserUseCase = Depends(get_create_team_uc),
) -> PortalUserResponse:
    data = CreateTeamUserInput(
        email=str(body.email), password=body.password, name=body.name, store_id=store_id,
        shop_role=body.shop_role, menu_permissions=body.menu_permissions,
        can_see_unassigned_leads=body.can_see_unassigned_leads,
        can_edit_others_leads=body.can_edit_others_leads,
    )
    u = await uc.execute(data)
    return PortalUserResponse(
        id=u.id, email=u.email, name=u.name, role=u.role, active=u.active,
        shop_role=u.shop_role, can_edit_others_leads=u.can_edit_others_leads,
    )
