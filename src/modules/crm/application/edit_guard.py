"""Guard de ESCRITA de leads (decisão do cliente 23/07).

A leitura do quadro é livre para toda a equipe da loja (ver ``leads.py``); editar
o lead de OUTRO colaborador exige autorização — a flag ``can_edit_others_leads``,
concedida por admin/dono/gerente. Default restrito: a permissão é concedida,
nunca retirada.
"""
from src.shared.domain.errors import ForbiddenError

_MESSAGE = "Este lead pertence a outro colaborador. Peça autorização ao gerente."


async def assert_can_edit_lead(user: object, lead: dict[str, object], users_repo: object) -> None:
    """Levanta ForbiddenError (403) se o usuário não pode escrever neste lead.

    admin, dono (client) e gerente da loja editam qualquer lead. shop_user comum
    edita apenas os leads em que é o responsável (``assigned_to``) ou o vendedor
    (``vendedor_id``) — a menos que tenha ``can_edit_others_leads``.
    """
    if getattr(user, "role", None) != "shop_user":
        return

    uid = getattr(user, "user_id", None)
    u = await users_repo.get_by_id(uid) if uid else None  # type: ignore[attr-defined]
    if u is None:
        raise ForbiddenError(_MESSAGE)
    if getattr(u, "shop_role", None) == "gerente":
        return
    if getattr(u, "can_edit_others_leads", False):
        return

    if uid not in (lead.get("assigned_to"), lead.get("vendedor_id")):
        raise ForbiddenError(_MESSAGE)
