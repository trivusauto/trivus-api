from typing import cast

from src.shared.domain.errors import DomainError


class CreatePlanUseCase:
    def __init__(self, plans, services) -> None:  # type: ignore[no-untyped-def]
        self._plans = plans
        self._services = services

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        if await self._plans.get_by_key(data["key"]):
            raise DomainError("Já existe um plano com essa key.")
        for key in cast(list[str], data.get("service_keys") or []):
            if await self._services.get_by_key(key) is None:
                raise DomainError(f"Serviço inexistente no catálogo: {key}")
        return cast(dict[str, object], await self._plans.create(data))


class UpdatePlanUseCase:
    def __init__(self, plans, services) -> None:  # type: ignore[no-untyped-def]
        self._plans = plans
        self._services = services

    async def execute(self, plan_id: str, data: dict[str, object]) -> dict[str, object]:
        data = dict(data)
        data.pop("key", None)
        if "service_keys" in data:
            for key in cast(list[str], data["service_keys"] or []):
                if await self._services.get_by_key(key) is None:
                    raise DomainError(f"Serviço inexistente no catálogo: {key}")
        return cast(dict[str, object], await self._plans.update(plan_id, data))
