from src.modules.action_plans.infrastructure.repository import ActionPlanRepository
from src.shared.domain.errors import NotFoundError


class StepsUseCase:
    """CRUD das etapas de um plano. Confere que o plano existe (404 amigável)."""

    def __init__(self, repo: ActionPlanRepository) -> None:
        self._repo = repo

    async def list(self, plan_id: str) -> list[dict[str, object]]:
        if await self._repo.get(plan_id) is None:
            raise NotFoundError("Plano de ação não encontrado.")
        return await self._repo.list_steps(plan_id)

    async def create(self, plan_id: str, data: dict[str, object]) -> dict[str, object]:
        if await self._repo.get(plan_id) is None:
            raise NotFoundError("Plano de ação não encontrado.")
        return await self._repo.create_step(plan_id, data)

    async def update(self, step_id: str, data: dict[str, object]) -> dict[str, object]:
        result = await self._repo.update_step(step_id, data)
        if result is None:
            raise NotFoundError("Etapa não encontrada.")
        return result

    async def delete(self, step_id: str) -> None:
        await self._repo.delete_step(step_id)


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
