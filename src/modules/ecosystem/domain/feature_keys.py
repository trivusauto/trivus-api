"""Registro versionado das feature keys — a verdade do que o código gateia.
Grão livre: módulo, tela, card ou área (convenção modulo.tela.area).
O CRUD de serviços aponta para estas keys via picklist (GET /ecosystem/feature-keys)."""

ALL_FEATURE_KEYS: dict[str, dict[str, str]] = {
    "crm.kanban": {"label": "CRM — Kanban de leads", "kind": "tela"},
    "crm.activity_log": {"label": "CRM — Histórico de atividades", "kind": "area"},
    "agenda": {"label": "Agenda", "kind": "tela"},
    "webhook.zapi": {"label": "Captação automática WhatsApp", "kind": "modulo"},
    "metrics.dashboard": {"label": "Dashboard de KPIs", "kind": "tela"},
    "metrics.reports": {"label": "Relatórios por origem", "kind": "tela"},
    "metrics.reports.costs": {"label": "Relatórios — coluna de custos (CPL…CAC)", "kind": "area"},
    "metrics.marketing": {"label": "Marketing — funil de custos", "kind": "tela"},
    "metrics.projections": {"label": "Projeções", "kind": "tela"},
    "metrics.team": {"label": "Performance da equipe", "kind": "tela"},
    "marketing.campaigns": {"label": "Cadastro de campanhas", "kind": "tela"},
    "bulk_send": {"label": "Disparos em massa", "kind": "modulo"},
    "indicators": {"label": "Modo indicadores", "kind": "tela"},
    "goals": {"label": "Metas", "kind": "tela"},
    "action_plans": {"label": "Planos de ação", "kind": "tela"},
}


def is_valid_feature_key(key: str) -> bool:
    return key in ALL_FEATURE_KEYS


def list_feature_keys() -> list[dict[str, str]]:
    return [{"key": k, **v} for k, v in ALL_FEATURE_KEYS.items()]
