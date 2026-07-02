from src.modules.action_plans.infrastructure.repository import ActionPlanRepository


class ListActionPlansUseCase:
    def __init__(self, repo: ActionPlanRepository) -> None:
        self._repo = repo

    async def execute(self, store_id: str) -> list[dict[str, object]]:
        return await self._repo.list_for_store(store_id)


class CreateActionPlanUseCase:
    def __init__(self, repo: ActionPlanRepository) -> None:
        self._repo = repo

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        return await self._repo.create(data)


class UpdateActionPlanUseCase:
    def __init__(self, repo: ActionPlanRepository) -> None:
        self._repo = repo

    async def execute(self, plan_id: str, data: dict[str, object]) -> dict[str, object]:
        return await self._repo.update(plan_id, data)


class DeleteActionPlanUseCase:
    def __init__(self, repo: ActionPlanRepository) -> None:
        self._repo = repo

    async def execute(self, plan_id: str) -> None:
        await self._repo.delete(plan_id)
