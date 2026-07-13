from typing import cast

from src.modules.ecosystem.domain.feature_keys import is_valid_feature_key
from src.shared.domain.errors import DomainError

_TYPES = ("software", "humano")


def _validate_feature_keys(keys: list[str]) -> None:
    invalid = [k for k in (keys or []) if not is_valid_feature_key(k)]
    if invalid:
        raise DomainError(f"feature key inválida: {', '.join(invalid)}")


class CreateServiceUseCase:
    def __init__(self, services) -> None:  # type: ignore[no-untyped-def]
        self._services = services

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        if data.get("type") not in _TYPES:
            raise DomainError("type deve ser software ou humano")
        _validate_feature_keys(cast(list[str], data.get("feature_keys") or []))
        if await self._services.get_by_key(data["key"]):
            raise DomainError("Já existe um serviço com essa key.")
        return cast(dict[str, object], await self._services.create(data))


class UpdateServiceUseCase:
    def __init__(self, services) -> None:  # type: ignore[no-untyped-def]
        self._services = services

    async def execute(self, service_id: str, data: dict[str, object]) -> dict[str, object]:
        data = dict(data)
        data.pop("key", None)                       # key é imutável (planos referenciam por key)
        if "feature_keys" in data:
            _validate_feature_keys(cast(list[str], data["feature_keys"] or []))
        return cast(dict[str, object], await self._services.update(service_id, data))


class DeactivateServiceUseCase:
    """Soft-delete: bloqueado se o serviço estiver em algum plano."""

    def __init__(self, services, plans) -> None:  # type: ignore[no-untyped-def]
        self._services = services
        self._plans = plans

    async def execute(self, service_id: str) -> dict[str, object]:
        svc = await self._services.get_or_raise(service_id)
        for plan in await self._plans.list_all():
            if svc["key"] in (plan.get("service_keys") or []):
                raise DomainError(f"Serviço está no plano '{plan['key']}' — remova do plano antes de desativar.")
        return cast(dict[str, object], await self._services.update(service_id, {"active": False}))
