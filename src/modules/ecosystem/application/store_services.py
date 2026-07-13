from src.shared.domain.errors import DomainError


class ToggleStoreServiceUseCase:
    """Liga/desliga um serviço numa loja — modelo híbrido: validado contra o plano
    da empresa ao ligar; desligar é sempre permitido."""

    def __init__(self, store_services, subscriptions, plans, company_stores) -> None:  # type: ignore[no-untyped-def]
        self._store_services = store_services
        self._subs = subscriptions
        self._plans = plans
        self._company_stores = company_stores

    async def execute(self, store_id: str, service_key: str, enabled: bool) -> None:
        if enabled:
            company_id = await self._company_stores.store_company(store_id)
            if company_id is None:
                raise DomainError("Loja sem empresa vinculada (modo legado) — vincule a uma empresa antes.")
            sub = await self._subs.current_for_company(company_id)
            if sub is None:
                raise DomainError("Empresa sem assinatura.")
            plan = await self._plans.get_or_raise(sub["plan_id"])
            if service_key not in (plan.get("service_keys") or []):
                raise DomainError(f"O serviço '{service_key}' não faz parte do plano da empresa.")
        await self._store_services.set_service(store_id, service_key, enabled)
