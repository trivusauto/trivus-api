from fastapi import APIRouter, Body, Depends

from src.modules.stores.application.create_store import CreateStoreUseCase
from src.modules.stores.application.dto import CreateStoreInput
from src.modules.stores.application.list_stores import ListStoresUseCase
from src.modules.stores.application.role_labels import GetRoleLabelsUseCase, SetRoleLabelsUseCase
from src.modules.stores.application.update_store import UpdateStoreUseCase
from src.modules.stores.domain.entities import Store
from src.modules.stores.interface.deps import (
    get_create_store_uc,
    get_list_stores_uc,
    get_role_labels_uc,
    get_update_store_uc,
    set_role_labels_uc,
)
from src.modules.stores.interface.schemas import CreateStoreRequest, StoreResponse
from src.shared.interface.auth_deps import CurrentUser
from src.shared.interface.rbac import require_roles

router = APIRouter(prefix="/admin/stores", tags=["stores"])


def _resp(s: Store) -> StoreResponse:
    return StoreResponse(id=s.id, nome_fantasia=s.nome_fantasia, crm_enabled=s.crm_enabled, active=s.active)


@router.get("")
async def list_stores(
    _: CurrentUser = Depends(require_roles("admin")),
    uc: ListStoresUseCase = Depends(get_list_stores_uc),
) -> list[StoreResponse]:
    return [_resp(s) for s in await uc.execute()]


@router.post("", status_code=201)
async def create_store(
    body: CreateStoreRequest,
    _: CurrentUser = Depends(require_roles("admin")),
    uc: CreateStoreUseCase = Depends(get_create_store_uc),
) -> StoreResponse:
    data = CreateStoreInput(
        nome_fantasia=body.nome_fantasia,
        fields={"razao_social": body.razao_social, "cnpj": body.cnpj},
    )
    return _resp(await uc.execute(data))


@router.patch("/{store_id}")
async def update_store(
    store_id: str,
    body: dict[str, object] = Body(...),
    _: CurrentUser = Depends(require_roles("admin")),
    uc: UpdateStoreUseCase = Depends(get_update_store_uc),
) -> StoreResponse:
    return _resp(await uc.execute(store_id, body))


@router.get("/{store_id}/role-labels")
async def get_role_labels(
    store_id: str,
    _: CurrentUser = Depends(require_roles("admin", "client")),
    uc: GetRoleLabelsUseCase = Depends(get_role_labels_uc),
) -> dict[str, str]:
    return await uc.execute(store_id)


@router.patch("/{store_id}/role-labels")
async def set_role_labels_endpoint(
    store_id: str,
    body: dict[str, str] = Body(...),
    _: CurrentUser = Depends(require_roles("admin", "client")),
    uc: SetRoleLabelsUseCase = Depends(set_role_labels_uc),
) -> dict[str, str]:
    return await uc.execute(store_id, body)
