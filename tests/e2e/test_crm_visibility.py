"""Visibilidade do quadro de CRM + filtro por responsável.

Regra NOVA (decisão do cliente 23/07, substitui a do legado):
- TODO usuário com acesso à loja vê o quadro INTEIRO, qualquer que seja o papel;
- a restrição passou a ser de ESCRITA (ver ``test_crm_edit_guard.py``);
- ``assigned_to`` é filtro de exibição — agora vale para todos, inclusive SDR.

``can_see_unassigned_leads`` continua existindo para o round-robin do webhook,
mas NÃO restringe mais a leitura.
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient


async def _admin(client: AsyncClient) -> dict[str, str]:
    r = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _store_with_funnel(client, headers, name):
    await client.post("/admin/crm/templates", json={"name": f"tpl-{name}", "stages": ["RECEBIDOS", "AGENDADOS"]}, headers=headers)
    st = (await client.post("/admin/stores", json={"nome_fantasia": name}, headers=headers)).json()
    await client.patch(f"/admin/stores/{st['id']}", json={"crm_enabled": True}, headers=headers)
    f = (await client.get(f"/crm/funnels?store_id={st['id']}", headers=headers)).json()
    return st["id"], f[0]["stages"][0]["id"]


async def _team(client, headers, store_id, shop_role, unassigned, can_edit=False):
    email = f"{shop_role}.{uuid4().hex[:8]}@trivus.com.br"
    u = (await client.post(
        f"/stores/{store_id}/team",
        json={"email": email, "password": "segredo1", "name": shop_role,
              "shop_role": shop_role, "can_see_unassigned_leads": unassigned,
              "can_edit_others_leads": can_edit},
        headers=headers,
    )).json()
    login = await client.post("/auth/login", json={"email": email, "password": "segredo1"})
    return u["id"], {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _lead(client, headers, store_id, stage_id, nome, assigned_to):
    body = {"store_id": store_id, "stage_id": stage_id, "funil": "receptivo",
            "nome": nome, "telefone": "(11) 90000-0000"}
    if assigned_to is not None:
        body["assigned_to"] = assigned_to
    return (await client.post("/crm/leads", json=body, headers=headers)).json()["id"]


def _names(rows) -> set[str]:
    return {r["nome"] for r in rows}


@pytest.mark.asyncio
async def test_leitura_liberada_para_toda_a_equipe(client: AsyncClient) -> None:
    """Todos os papéis veem o quadro inteiro — inclusive o SDR."""
    admin = await _admin(client)
    sid, stage = await _store_with_funnel(client, admin, "Loja visibilidade")

    ger_id, ger = await _team(client, admin, sid, "gerente", True)
    sdr_id, sdr = await _team(client, admin, sid, "sdr", False)
    fin_id, fin = await _team(client, admin, sid, "administrativo", True)

    await _lead(client, admin, sid, stage, "L_SDR", sdr_id)
    await _lead(client, admin, sid, stage, "L_GER", ger_id)
    await _lead(client, admin, sid, stage, "L_FIN", fin_id)
    await _lead(client, admin, sid, stage, "L_NONE", None)

    async def board(h, qs=""):
        r = await client.get(f"/crm/leads?store_id={sid}{qs}", headers=h)
        assert r.status_code == 200, r.text
        return _names(r.json())

    todos = {"L_SDR", "L_GER", "L_FIN", "L_NONE"}
    assert await board(admin) == todos
    assert await board(ger) == todos
    assert await board(sdr) == todos, "SDR agora vê o quadro inteiro"
    assert await board(fin) == todos


@pytest.mark.asyncio
async def test_board_traz_nome_do_responsavel(client: AsyncClient) -> None:
    """O payload do board inclui assigned_to_name (para o filtro 'Responsável')."""
    admin = await _admin(client)
    sid, stage = await _store_with_funnel(client, admin, "Loja resp nome")
    sdr_id, _ = await _team(client, admin, sid, "sdr", False)

    await _lead(client, admin, sid, stage, "L_COM_RESP", sdr_id)
    await _lead(client, admin, sid, stage, "L_SEM_RESP", None)

    rows = (await client.get(f"/crm/leads?store_id={sid}", headers=admin)).json()
    by_name = {r["nome"]: r for r in rows}
    assert by_name["L_COM_RESP"]["assigned_to_name"] == "sdr"
    assert by_name["L_SEM_RESP"]["assigned_to_name"] is None


@pytest.mark.asyncio
async def test_filtro_por_responsavel_vale_para_todos(client: AsyncClient) -> None:
    """O filtro 'Responsável' agora funciona para qualquer papel."""
    admin = await _admin(client)
    sid, stage = await _store_with_funnel(client, admin, "Loja filtro resp")

    ger_id, ger = await _team(client, admin, sid, "gerente", True)
    sdr_id, sdr = await _team(client, admin, sid, "sdr", False)

    await _lead(client, admin, sid, stage, "L_SDR", sdr_id)
    await _lead(client, admin, sid, stage, "L_GER", ger_id)
    await _lead(client, admin, sid, stage, "L_NONE", None)

    async def board(h, qs=""):
        r = await client.get(f"/crm/leads?store_id={sid}{qs}", headers=h)
        assert r.status_code == 200, r.text
        return _names(r.json())

    assert await board(admin, f"&assigned_to={sdr_id}") == {"L_SDR"}
    assert await board(admin, "&assigned_to=__unassigned__") == {"L_NONE"}
    assert await board(ger, f"&assigned_to={ger_id}") == {"L_GER"}
    # o SDR pode filtrar pelos leads do colega (só LEITURA — editar é outro guard)
    assert await board(sdr, f"&assigned_to={ger_id}") == {"L_GER"}


@pytest.mark.asyncio
async def test_loja_alheia_continua_bloqueada(client: AsyncClient) -> None:
    """Liberar a leitura dentro da loja não afeta o isolamento entre lojas."""
    admin = await _admin(client)
    sid_a, stage_a = await _store_with_funnel(client, admin, "Loja iso A")
    sid_b, _ = await _store_with_funnel(client, admin, "Loja iso B")

    _, sdr_a = await _team(client, admin, sid_a, "sdr", False)
    await _lead(client, admin, sid_a, stage_a, "L_A", None)

    r = await client.get(f"/crm/leads?store_id={sid_b}", headers=sdr_a)
    assert r.status_code == 403
