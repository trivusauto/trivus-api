from typing import cast


class GetCatalogUseCase:
    """Catálogo p/ a loja: cada serviço com unlocked=True/False + mapa feature_key→serviço
    que a desbloqueia (é assim que o front sabe qual card de upsell mostrar em cada área)."""

    def __init__(self, services, entitlements) -> None:  # type: ignore[no-untyped-def]
        self._services = services
        self._entitlements = entitlements

    async def execute(self, store_id: str) -> dict[str, object]:
        unlocked_keys = await self._entitlements.feature_keys_for_store(store_id)
        catalog: list[dict[str, object]] = []
        unlockers: dict[str, dict[str, object]] = {}
        for svc in await self._services.list_all(only_active=True):
            svc_keys = set(cast(list[str], svc.get("feature_keys") or []))
            catalog.append({
                "key": svc["key"], "name": svc["name"], "type": svc["type"],
                "what_it_is": svc.get("what_it_is"), "what_it_does": svc.get("what_it_does"),
                "upsell_pitch": svc.get("upsell_pitch"),
                "unlocked": bool(svc_keys) and svc_keys.issubset(unlocked_keys),
            })
            for fk in svc_keys - unlocked_keys:
                unlockers.setdefault(fk, {"service_key": svc["key"], "name": svc["name"],
                                          "upsell_pitch": svc.get("upsell_pitch")})
        return {"services": catalog, "unlocked_feature_keys": sorted(unlocked_keys),
                "locked_unlockers": unlockers}


class RegisterInterestUseCase:
    def __init__(self, interests, company_stores, notifier) -> None:  # type: ignore[no-untyped-def]
        self._interests = interests
        self._company_stores = company_stores
        self._notifier = notifier

    async def execute(self, store_id: str, service_key: str, user_id: str) -> dict[str, object]:
        company_id = await self._company_stores.store_company(store_id)
        interest = await self._interests.create({"company_id": company_id, "store_id": store_id,
                                                 "service_key": service_key, "requested_by": user_id,
                                                 "status": "novo"})
        await self._notifier.notify(interest)
        return cast(dict[str, object], interest)
