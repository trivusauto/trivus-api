from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.action_plans.application.use_cases import (
    CreateActionPlanUseCase, DeleteActionPlanUseCase, ListActionPlansUseCase, UpdateActionPlanUseCase,
)
from src.modules.action_plans.infrastructure.repository import ActionPlanRepository
from src.shared.infrastructure.database import get_session


def _repo(session: AsyncSession = Depends(get_session)) -> ActionPlanRepository:
    return ActionPlanRepository(session)


def list_uc(r: ActionPlanRepository = Depends(_repo)) -> ListActionPlansUseCase:
    return ListActionPlansUseCase(r)


def create_uc(r: ActionPlanRepository = Depends(_repo)) -> CreateActionPlanUseCase:
    return CreateActionPlanUseCase(r)


def update_uc(r: ActionPlanRepository = Depends(_repo)) -> UpdateActionPlanUseCase:
    return UpdateActionPlanUseCase(r)


def delete_uc(r: ActionPlanRepository = Depends(_repo)) -> DeleteActionPlanUseCase:
    return DeleteActionPlanUseCase(r)
