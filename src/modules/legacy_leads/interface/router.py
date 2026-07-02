from fastapi import APIRouter, Depends, Query
from src.modules.legacy_leads.application.use_cases import (
    CreateLegacyLeadUseCase, DeleteLegacyLeadUseCase, ListLegacyLeadsUseCase, UpdateLegacyLeadUseCase,
)
from src.modules.legacy_leads.interface.deps import create_uc, delete_uc, list_uc, update_uc
from src.modules.legacy_leads.interface.schemas import CreateLegacyLeadRequest, UpdateLegacyLeadRequest
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(prefix="/leads", tags=["legacy-leads"])


@router.get("")
async def list_leads(
    store_id: str = Query(...),
    _: CurrentUser = Depends(get_current_user),
    uc: ListLegacyLeadsUseCase = Depends(list_uc),
) -> list[dict[str, object]]:
    return await uc.execute(store_id)


@router.post("", status_code=201)
async def create_lead(
    body: CreateLegacyLeadRequest,
    _: CurrentUser = Depends(get_current_user),
    uc: CreateLegacyLeadUseCase = Depends(create_uc),
) -> dict[str, object]:
    return await uc.execute(body.model_dump(exclude_none=True))


@router.patch("/{lead_id}")
async def update_lead(
    lead_id: str,
    body: UpdateLegacyLeadRequest,
    _: CurrentUser = Depends(get_current_user),
    uc: UpdateLegacyLeadUseCase = Depends(update_uc),
) -> dict[str, object]:
    return await uc.execute(lead_id, body.model_dump(exclude_none=True))


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: str,
    _: CurrentUser = Depends(get_current_user),
    uc: DeleteLegacyLeadUseCase = Depends(delete_uc),
) -> None:
    await uc.execute(lead_id)
