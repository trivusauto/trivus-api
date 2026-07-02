from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.goals.application.use_cases import DeleteGoalUseCase, ListGoalsUseCase, UpsertGoalUseCase
from src.modules.goals.infrastructure.repository import GoalRepository
from src.shared.infrastructure.database import get_session


def _repo(session: AsyncSession = Depends(get_session)) -> GoalRepository:
    return GoalRepository(session)


def list_uc(r: GoalRepository = Depends(_repo)) -> ListGoalsUseCase:
    return ListGoalsUseCase(r)


def upsert_uc(r: GoalRepository = Depends(_repo)) -> UpsertGoalUseCase:
    return UpsertGoalUseCase(r)


def delete_uc(r: GoalRepository = Depends(_repo)) -> DeleteGoalUseCase:
    return DeleteGoalUseCase(r)
