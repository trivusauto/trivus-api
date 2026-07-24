from fastapi import APIRouter, Depends, Query
from src.modules.action_plans.application.use_cases import (
    CreateActionPlanUseCase, DeleteActionPlanUseCase, ListActionPlansUseCase, UpdateActionPlanUseCase,
)
from src.modules.action_plans.application.use_cases import StepsUseCase
from src.modules.action_plans.interface.deps import create_uc, delete_uc, list_uc, steps_uc, update_uc
from src.modules.action_plans.interface.schemas import (
    CreateActionPlanRequest, CreateStepRequest, UpdateActionPlanRequest, UpdateStatusRequest,
    UpdateStepRequest,
)
from src.shared.interface.feature_gate import require_feature
from src.shared.interface.auth_deps import get_current_user
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["action-plans"])
admin_router = APIRouter(tags=["action-plans"])


@router.get("/action-plans", dependencies=[Depends(require_feature("action_plans"))])
async def list_plans(
    store_id: str = Query(...),
    _: object = Depends(get_current_user),
    uc: ListActionPlansUseCase = Depends(list_uc),
) -> list[dict[str, object]]:
    return await uc.execute(store_id)


@router.patch("/action-plans/{plan_id}/status")
async def update_status(
    plan_id: str,
    body: UpdateStatusRequest,
    _: object = Depends(get_current_user),
    uc: UpdateActionPlanUseCase = Depends(update_uc),
) -> dict[str, object]:
    return await uc.execute(plan_id, {"status": body.status})


@router.get("/action-plans/{plan_id}/steps")
async def list_steps(
    plan_id: str,
    _: object = Depends(get_current_user),
    uc: StepsUseCase = Depends(steps_uc),
) -> list[dict[str, object]]:
    return await uc.list(plan_id)


@router.post("/action-plans/{plan_id}/steps", status_code=201)
async def create_step(
    plan_id: str,
    body: CreateStepRequest,
    _: object = Depends(get_current_user),
    uc: StepsUseCase = Depends(steps_uc),
) -> dict[str, object]:
    return await uc.create(plan_id, body.model_dump(exclude_none=True))


@router.patch("/action-plans/{plan_id}/steps/{step_id}")
async def update_step(
    plan_id: str,
    step_id: str,
    body: UpdateStepRequest,
    _: object = Depends(get_current_user),
    uc: StepsUseCase = Depends(steps_uc),
) -> dict[str, object]:
    return await uc.update(step_id, body.model_dump(exclude_unset=True))


@router.delete("/action-plans/{plan_id}/steps/{step_id}", status_code=204)
async def delete_step(
    plan_id: str,
    step_id: str,
    _: object = Depends(get_current_user),
    uc: StepsUseCase = Depends(steps_uc),
) -> None:
    await uc.delete(step_id)


@admin_router.post("/admin/action-plans", status_code=201)
async def create_plan(
    body: CreateActionPlanRequest,
    _: object = Depends(require_roles("admin")),
    uc: CreateActionPlanUseCase = Depends(create_uc),
) -> dict[str, object]:
    return await uc.execute(body.model_dump(exclude_none=True))


@admin_router.patch("/admin/action-plans/{plan_id}")
async def update_plan(
    plan_id: str,
    body: UpdateActionPlanRequest,
    _: object = Depends(require_roles("admin")),
    uc: UpdateActionPlanUseCase = Depends(update_uc),
) -> dict[str, object]:
    return await uc.execute(plan_id, body.model_dump(exclude_none=True))


@admin_router.delete("/admin/action-plans/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: str,
    _: object = Depends(require_roles("admin")),
    uc: DeleteActionPlanUseCase = Depends(delete_uc),
) -> None:
    await uc.execute(plan_id)
