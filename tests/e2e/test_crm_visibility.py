"""Visibilidade do quadro de CRM por papel (espelha o legado) + filtro por responsável.

Regra (trivus/app/crm/page.js:497-503):
- admin / dono (client) → veem o funil inteiro da loja;
- shop_user gerente → vê tudo;
- shop_user com can_see_unassigned_leads → próprios + não atribuídos;
- demais shop_users (sdr, vendedor) → só os próprios.
O parâmetro ``assigned_to`` apenas restringe dentro do que já é visível (nunca amplia).
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


async def _team(client, headers, store_id, shop_role, unassigned):
    email = f"{shop_role}.{uuid4().hex[:8]}@trivus.com.br"
    u = (await client.post(
        f"/stores/{store_id}/team",
        json={"email": email, "password": "segredo1", "name": shop_role,
              "shop_role": shop_role, "can_see_unassigned_leads": unassigned},
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
async def test_visibilidade_por_papel(client: AsyncClient) -> None:
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

    # admin e gerente veem tudo
    assert await board(admin) == {"L_SDR", "L_GER", "L_FIN", "L_NONE"}
    assert await board(ger) == {"L_SDR", "L_GER", "L_FIN", "L_NONE"}
    # sdr só o próprio
    assert await board(sdr) == {"L_SDR"}
    # administrativo: próprios + não atribuídos
    assert await board(fin) == {"L_FIN", "L_NONE"}


@pytest.mark.asyncio
async def test_filtro_por_responsavel(client: AsyncClient) -> None:
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

    # filtro do gestor por responsável específico e por não atribuídos
    assert await board(admin, f"&assigned_to={sdr_id}") == {"L_SDR"}
    assert await board(admin, "&assigned_to=__unassigned__") == {"L_NONE"}
    assert await board(ger, f"&assigned_to={ger_id}") == {"L_GER"}
    # sdr restrito não amplia acesso: filtrar por outro responsável não vaza nada
    assert await board(sdr, f"&assigned_to={ger_id}") == set()
