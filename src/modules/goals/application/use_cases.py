from src.modules.goals.infrastructure.repository import GoalRepository


class ListGoalsUseCase:
    def __init__(self, repo: GoalRepository) -> None:
        self._repo = repo

    async def execute(self, store_id: str, year: int, month: int) -> list[dict[str, object]]:
        return await self._repo.list(store_id, year, month)


class UpsertGoalUseCase:
    def __init__(self, repo: GoalRepository) -> None:
        self._repo = repo

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        return await self._repo.upsert(data)


class DeleteGoalUseCase:
    def __init__(self, repo: GoalRepository) -> None:
        self._repo = repo

    async def execute(self, goal_id: str) -> None:
        await self._repo.delete(goal_id)
