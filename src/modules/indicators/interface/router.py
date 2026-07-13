from fastapi import APIRouter, Depends, Query
from src.modules.indicators.application.use_cases import ListIndicatorsUseCase, UpsertIndicatorUseCase
from src.modules.indicators.interface.deps import list_uc, upsert_uc
from src.modules.indicators.interface.schemas import UpsertIndicatorRequest
from src.shared.interface.feature_gate import require_feature
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("", dependencies=[Depends(require_feature("indicators"))])
async def list_indicators(
    store_id: str = Query(...),
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    _: CurrentUser = Depends(get_current_user),
    uc: ListIndicatorsUseCase = Depends(list_uc),
) -> list[dict[str, object]]:
    return await uc.execute(store_id, date_from, date_to)


@router.post("", status_code=201)
async def upsert_indicator(
    body: UpsertIndicatorRequest,
    _: CurrentUser = Depends(get_current_user),
    uc: UpsertIndicatorUseCase = Depends(upsert_uc),
) -> dict[str, object]:
    await uc.execute(body.model_dump(exclude_none=True))
    return {"ok": True}
