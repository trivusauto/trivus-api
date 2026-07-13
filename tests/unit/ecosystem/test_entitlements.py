from datetime import date

from src.modules.ecosystem.domain.entitlements import resolve_feature_keys, subscription_usable

TODAY = date(2026, 7, 15)
SERVICES: list[dict[str, object]] = [
    {"key": "crm_completo", "active": True, "feature_keys": ["crm.kanban", "agenda"]},
    {"key": "metricas_avancadas", "active": True, "feature_keys": ["metrics.marketing", "metrics.projections"]},
    {"key": "consultoria", "active": True, "feature_keys": []},
]


def test_active_subscription_usable() -> None:
    assert subscription_usable({"status": "active"}, TODAY) is True
    assert subscription_usable({"status": "suspended"}, TODAY) is False
    assert subscription_usable(None, TODAY) is False


def test_trial_expires_on_read() -> None:
    assert subscription_usable({"status": "trialing", "trial_ends_at": "2026-07-15"}, TODAY) is True
    assert subscription_usable({"status": "trialing", "trial_ends_at": "2026-07-14"}, TODAY) is False
    assert subscription_usable({"status": "trialing", "trial_ends_at": None}, TODAY) is False


def test_resolution_chain() -> None:
    sub: dict[str, object] = {"status": "active"}
    keys = resolve_feature_keys(sub, plan_service_keys=["crm_completo", "metricas_avancadas"],
                                enabled_service_keys=["crm_completo"], services=SERVICES, today=TODAY)
    assert keys == {"crm.kanban", "agenda"}          # métricas permitida no plano mas desligada na loja


def test_unusable_subscription_blocks_all() -> None:
    keys = resolve_feature_keys({"status": "canceled"}, ["crm_completo"], ["crm_completo"], SERVICES, TODAY)
    assert keys == set()


def test_inactive_service_excluded() -> None:
    services: list[dict[str, object]] = [{"key": "crm_completo", "active": False, "feature_keys": ["crm.kanban"]}]
    keys = resolve_feature_keys({"status": "active"}, ["crm_completo"], ["crm_completo"], services, TODAY)
    assert keys == set()
