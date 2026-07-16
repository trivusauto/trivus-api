"""E2E dos patches de lead que escrevem DATAS (agendamento/comparecimento/fechamento).

Regressão do bug: LeadPatch produz datas como string ISO ("2026-07-20") e as
colunas são DATE — o asyncpg exige datetime.date, então o PATCH estourava 500.
"""
import pytest
from httpx import AsyncClient


async def _admin(client: AsyncClient) -> dict[str, str]:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _store_with_funnel(client: AsyncClient, headers: dict[str, str]) -> tuple[str, str]:
    """Cria template + loja com CRM ligado e devolve (store_id, primeira_stage_id)."""
    await client.post(
        "/admin/crm/templates",
        json={"name": "Tpl Patches", "stages": ["RECEBIDOS", "AGENDADOS"]},
        headers=headers,
    )
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Patches"}, headers=headers)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"crm_enabled": True}, headers=headers)
    funnels = (await client.get(f"/crm/funnels?store_id={store['id']}", headers=headers)).json()
    assert funnels, "loja com crm_enabled deveria ter funil clonado do template"
    return store["id"], funnels[0]["stages"][0]["id"]


@pytest.mark.asyncio
async def test_agendamento_comparecimento_fechamento_com_datas_iso(client: AsyncClient) -> None:
    headers = await _admin(client)
    store_id, stage_id = await _store_with_funnel(client, headers)
    lead = (await client.post(
        "/crm/leads",
        json={"store_id": store_id, "stage_id": stage_id, "funil": "receptivo", "nome": "Lead Datas", "telefone": "(11) 90000-0001"},
        headers=headers,
    )).json()

    # agendamento: strings ISO como o front/agente mandam → 200 e campos derivados
    res = await client.patch(
        f"/crm/leads/{lead['id']}/agendamento",
        json={"data_agendamento": "2026-07-20", "hora_agendamento": "14:30"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["data_agendamento"] == "2026-07-20"
    assert body["hora_agendamento"] == "14:30:00"
    assert body["agendado_por"] is not None
    assert body["data_marcacao_agendamento"] is not None

    # comparecimento: seta data_compareceu (string ISO internamente)
    res = await client.patch(f"/crm/leads/{lead['id']}/comparecimento", json={"compareceu": True}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["compareceu_agendamento"] is True
    assert res.json()["data_compareceu"] is not None

    # fechamento: seta data_fechou_negocio + valores monetários em string
    res = await client.patch(
        f"/crm/leads/{lead['id']}/fechamento",
        json={"receita": "10000", "despesa": "8000", "rentabilidade": "2000"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["fechou_negocio"] is True
    assert res.json()["data_fechou_negocio"] is not None

    # cancelamento: nulls limpam agendamento e agendado_por
    res = await client.patch(
        f"/crm/leads/{lead['id']}/agendamento",
        json={"data_agendamento": None, "hora_agendamento": None},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["data_agendamento"] is None
    assert res.json()["agendado_por"] is None
