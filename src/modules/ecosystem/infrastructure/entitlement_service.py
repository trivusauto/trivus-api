from datetime import date
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.ecosystem.domain.entitlements import resolve_feature_keys
from src.modules.ecosystem.domain.feature_keys import ALL_FEATURE_KEYS
from src.modules.ecosystem.infrastructure.repositories import (
    PlanRepository, ServiceRepository, StoreServiceRepository, SubscriptionRepository,
)
from src.modules.stores.infrastructure.orm import StoreModel


class EntitlementService:
    """Resolve as feature keys desbloqueadas de uma loja (spec ECOSSISTEMA §3)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._subs = SubscriptionRepository(session)
        self._plans = PlanRepository(session)
        self._services = ServiceRepository(session)
        self._store_services = StoreServiceRepository(session)

    async def feature_keys_for_store(self, store_id: str) -> set[str]:
        store = await self._session.get(StoreModel, store_id)
        if store is None:
            return set()
        if store.company_id is None:
            # Loja sem empresa: acesso completo temporário — NÃO é isenção. A frente de
            # cobrança (futura) deve cobrar também lojas sem empresa (decisão Giovani
            # 24/07, ver AJUSTES_POS_REUNIAO_CLIENTE.md item 11).
            # União das feature_keys de todos os serviços de software ativos; se o
            # catálogo estiver vazio, cai no registro completo (equivalente ao Full).
            services = await self._services.list_all(only_active=True)
            union = {
                str(k)
                for svc in services
                for k in cast(list[str], svc.get("feature_keys") or [])
            }
            return union or set(ALL_FEATURE_KEYS)
        sub = await self._subs.current_for_company(str(store.company_id))
        if sub is None:
            return set()                          # E3: sem assinatura = tudo bloqueado
        plan = await self._plans.get(str(sub["plan_id"])) or {}
        enabled = await self._store_services.enabled_keys_for_store(store_id)
        services = await self._services.list_all(only_active=True)
        if store.crm_enabled:                     # legado: flag do CRM conta como 'ligado' p/ serviços com keys crm.*
            for svc in services:
                keys = cast(list[str], svc.get("feature_keys") or [])
                if any(str(k).startswith("crm.") for k in keys):
                    enabled.append(str(svc["key"]))
        plan_keys = [str(k) for k in cast(list[str], plan.get("service_keys") or [])]
        return resolve_feature_keys(sub, plan_keys, enabled, services, date.today())
