"""Regressão do stress test: isolamento multi-tenant + robustez de input (4xx, nunca 500)."""
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


@pytest.mark.asyncio
async def test_client_nao_acessa_loja_alheia(client: AsyncClient) -> None:
    headers = await _admin(client)
    a_id, _a_stage = await _store_with_funnel(client, headers, "Loja A own")
    b_id, b_stage = await _store_with_funnel(client, headers, "Loja B alheia")

    email = f"dono.a.{uuid4().hex[:8]}@trivus.com.br"
    owner = (await client.post("/admin/users", json={"email": email, "password": "segredo1", "name": "Dono A"}, headers=headers)).json()
    await client.put(f"/admin/users/{owner['id']}/stores", json={"store_ids": [a_id], "owner_store_ids": [a_id]}, headers=headers)
    login = await client.post("/auth/login", json={"email": email, "password": "segredo1"})
    oh = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert (await client.get(f"/crm/leads?store_id={a_id}", headers=oh)).status_code == 200
    assert (await client.get(f"/crm/funnels?store_id={a_id}", headers=oh)).status_code == 200
    assert (await client.get(f"/crm/leads?store_id={b_id}", headers=oh)).status_code == 403
    assert (await client.get(f"/crm/funnels?store_id={b_id}", headers=oh)).status_code == 403
    assert (await client.get(f"/agenda?store_id={b_id}&apply_to=agendamento&preset=month", headers=oh)).status_code == 403
    r = await client.post("/crm/leads", json={"store_id": b_id, "stage_id": b_stage, "funil": "receptivo", "nome": "x", "telefone": "(11) 90000-0000"}, headers=oh)
    assert r.status_code == 403, r.text


@pytest.mark.asyncio
async def test_input_invalido_nunca_500(client: AsyncClient) -> None:
    headers = await _admin(client)
    sid, stage = await _store_with_funnel(client, headers, "Loja robustez")
    lead = (await client.post("/crm/leads", json={"store_id": sid, "stage_id": stage, "funil": "receptivo", "nome": "r", "telefone": "(11) 91111-1111"}, headers=headers)).json()
    lid = lead["id"]

    assert (await client.patch(f"/crm/leads/{lid}", json={"valor_compra": "999999999999999999"}, headers=headers)).status_code == 400
    assert (await client.patch(f"/crm/leads/{lid}/agendamento", json={"data_agendamento": "2026-13-45", "hora_agendamento": "10:00"}, headers=headers)).status_code == 400
    assert (await client.patch(f"/crm/leads/{lid}", json={"data_comprado": "20/07/2026"}, headers=headers)).status_code == 400
    assert (await client.patch("/crm/leads/not-a-uuid", json={"nome": "x"}, headers=headers)).status_code == 404
    assert (await client.get(f"/metrics/projections?store_id={sid}&year=2026&month=13", headers=headers)).status_code == 400
