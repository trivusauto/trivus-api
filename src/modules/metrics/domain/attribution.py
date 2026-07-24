"""Regras de atribuição de métricas a um colaborador (portadas do legado
`trivus/lib/crmTeamMetrics.js`).

Cada etapa do funil pertence a uma pessoa diferente: quem PEGOU o lead não é
necessariamente quem AGENDOU nem quem VENDEU. Estas regras são a fonte única —
usadas pelas projeções por colaborador (S4.9) e pelo desempenho da equipe (S5.4).
"""


def _same(value: object, user_id: str) -> bool:
    return value is not None and str(value) == user_id


def owns_lead(lead: dict[str, object], user_id: str) -> bool:
    """Leads pegos → `assigned_to` (contados pela data de criação)."""
    return _same(lead.get("assigned_to"), user_id)


def owns_scheduling(lead: dict[str, object], user_id: str) -> bool:
    """Agendamentos → `vendedor_id`; se vazio, `agendado_por`."""
    vendedor = lead.get("vendedor_id")
    if vendedor is not None:
        return _same(vendedor, user_id)
    return _same(lead.get("agendado_por"), user_id)


def owns_attendance(lead: dict[str, object], user_id: str) -> bool:
    """Comparecimentos → `vendedor_id`."""
    return _same(lead.get("vendedor_id"), user_id)


def owns_closing(lead: dict[str, object], user_id: str) -> bool:
    """Fechamentos, receita e rentabilidade → `vendedor_id`."""
    return _same(lead.get("vendedor_id"), user_id)
