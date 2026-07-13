from datetime import date
from typing import cast


def subscription_usable(sub: dict[str, object] | None, today: date) -> bool:
    """active sempre; trialing só até trial_ends_at (expira na leitura, sem cron)."""
    if not sub:
        return False
    status = sub.get("status")
    if status == "active":
        return True
    if status == "trialing":
        te = sub.get("trial_ends_at")
        return bool(te and str(te)[:10] >= today.isoformat())
    return False


def resolve_feature_keys(sub: dict[str, object] | None, plan_service_keys: list[str],
                         enabled_service_keys: list[str], services: list[dict[str, object]],
                         today: date) -> set[str]:
    """Cadeia da spec §3: assinatura utilizável ∧ (plano permite ∩ ligado na loja)
    → união das feature_keys dos serviços ativos."""
    if not subscription_usable(sub, today):
        return set()
    allowed = set(plan_service_keys or []) & set(enabled_service_keys or [])
    keys: set[str] = set()
    for svc in services:
        if svc.get("key") in allowed and svc.get("active", True):
            keys.update(cast(list[str], svc.get("feature_keys") or []))
    return keys
