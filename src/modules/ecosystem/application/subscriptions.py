from src.shared.domain.errors import DomainError

_STATUSES = ("trialing", "active", "suspended", "canceled")


class CreateSubscriptionUseCase:
    def __init__(self, subscriptions, plans, company_stores) -> None:  # type: ignore[no-untyped-def]
        self._subs = subscriptions
        self._plans = plans
        self._company_stores = company_stores

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        if data.get("status") not in ("trialing", "active"):
            raise DomainError("Assinatura nasce como trialing ou active.")
        if data["status"] == "trialing" and not data.get("trial_ends_at"):
            raise DomainError("Assinatura em trial exige trial_ends_at (E2).")
        plan = await self._plans.get_or_raise(data["plan_id"])
        max_stores = plan.get("max_stores")
        if max_stores is not None:
            n = await self._company_stores.count_stores(data["company_id"])
            if n > int(max_stores):
                raise DomainError(f"O plano permite {max_stores} lojas; a empresa tem {n}.")
        return await self._subs.create({"billing_mode": "manual", **data})


class ChangeSubscriptionStatusUseCase:
    """suspend / reactivate / cancel — admin manual (v1)."""

    def __init__(self, subscriptions) -> None:  # type: ignore[no-untyped-def]
        self._subs = subscriptions

    async def execute(self, subscription_id: str, status: str) -> dict[str, object]:
        if status not in _STATUSES:
            raise DomainError("Status inválido.")
        return await self._subs.update(subscription_id, {"status": status})


class ChangeSubscriptionPlanUseCase:
    def __init__(self, subscriptions, plans) -> None:  # type: ignore[no-untyped-def]
        self._subs = subscriptions
        self._plans = plans

    async def execute(self, subscription_id: str, plan_id: str) -> dict[str, object]:
        await self._plans.get_or_raise(plan_id)
        return await self._subs.update(subscription_id, {"plan_id": plan_id})
