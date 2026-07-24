import uuid

import pytest
from httpx import AsyncClient


async def _admin(client: AsyncClient) -> dict[str, str]:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_agenda_empty_ok(client: AsyncClient) -> None:
    headers = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Ag"}, headers=headers)).json()
    res = await client.get(f"/agenda?store_id={store['id']}&apply_to=agendamento&preset=month", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == [] and body["total"] == 0 and body["page"] == 1


@pytest.mark.asyncio
async def test_agenda_filtra_por_vendedor_e_traz_nome(client: AsyncClient) -> None:
    """GET /agenda aceita vendedor_id e devolve vendedor_nome (S2.10)."""
    headers = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Ag Vend"}, headers=headers)).json()
    store_id = store["id"]
    await client.patch(f"/admin/stores/{store_id}", json={"crm_enabled": True}, headers=headers)

    # o banco de teste persiste entre rodadas — e-mail único evita colisão
    created = await client.post(
        f"/stores/{store_id}/team",
        json={
            "email": f"vend.agenda.{uuid.uuid4().hex[:8]}@example.com",
            "password": "demo123",
            "name": "Vendedor Agenda",
            "shop_role": "vendedor",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    vendedor = created.json()

    funnel = (await client.get(f"/crm/funnels?store_id={store_id}", headers=headers)).json()[0]
    stage_id = funnel["stages"][0]["id"]

    async def _lead_agendado(nome: str, telefone: str, vendedor_id: str | None) -> dict[str, object]:
        payload: dict[str, object] = {
            "store_id": store_id, "stage_id": stage_id, "funil": "receptivo",
            "nome": nome, "telefone": telefone,
        }
        lead = (await client.post("/crm/leads", json=payload, headers=headers)).json()
        if vendedor_id:
            res = await client.patch(
                f"/crm/leads/{lead['id']}", json={"vendedor_id": vendedor_id}, headers=headers
            )
            assert res.status_code == 200, res.text
        await client.patch(
            f"/crm/leads/{lead['id']}/agendamento",
            json={"data_agendamento": "2026-07-20", "hora_agendamento": "09:00"},
            headers=headers,
        )
        return dict(lead)

    com_vendedor = await _lead_agendado("Lead Com Vendedor", "(11) 90000-0201", vendedor["id"])
    await _lead_agendado("Lead Sem Vendedor", "(11) 90000-0202", None)

    base = f"/agenda?store_id={store_id}&apply_to=agendamento&preset=custom&from=2026-07-01&to=2026-07-31"

    todos = (await client.get(base, headers=headers)).json()
    assert todos["total"] == 2
    nomes = {item["id"]: item["vendedor_nome"] for item in todos["items"]}
    assert nomes[com_vendedor["id"]] == "Vendedor Agenda"

    filtrado = (await client.get(f"{base}&vendedor_id={vendedor['id']}", headers=headers)).json()
    assert filtrado["total"] == 1
    assert filtrado["items"][0]["id"] == com_vendedor["id"]
