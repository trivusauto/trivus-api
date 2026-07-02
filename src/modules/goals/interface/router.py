from fastapi import APIRouter, Depends, Query
from src.modules.goals.application.use_cases import DeleteGoalUseCase, ListGoalsUseCase, UpsertGoalUseCase
from src.modules.goals.interface.deps import delete_uc, list_uc, upsert_uc
from src.modules.goals.interface.schemas import UpsertGoalRequest
from src.shared.interface.auth_deps import get_current_user
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["goals"])
admin_router = APIRouter(tags=["goals"])


@router.get("/goals")
async def list_goals(
    store_id: str = Query(...),
    year: int = Query(...),
    month: int = Query(...),
    _: object = Depends(get_current_user),
    uc: ListGoalsUseCase = Depends(list_uc),
) -> list[dict[str, object]]:
    return await uc.execute(store_id, year, month)


@admin_router.post("/admin/goals", status_code=201)
async def create_goal(
    body: UpsertGoalRequest,
    _: object = Depends(require_roles("admin")),
    uc: UpsertGoalUseCase = Depends(upsert_uc),
) -> dict[str, object]:
    return await uc.execute(body.model_dump(exclude_none=True))


@admin_router.delete("/admin/goals/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: str,
    _: object = Depends(require_roles("admin")),
    uc: DeleteGoalUseCase = Depends(delete_uc),
) -> None:
    await uc.execute(goal_id)
