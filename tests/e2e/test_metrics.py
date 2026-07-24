import pytest
from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


@pytest.mark.asyncio
async def test_dashboard_empty(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/admin/stores", json={"nome_fantasia": "Metrics Store"}, headers=headers)
    store_id = created.json()["id"]
    res = await client.get(f"/metrics/dashboard?store_id={store_id}&start=2026-01-01&end=2026-12-31", headers=headers)
    assert res.status_code == 200
    assert res.json()["totals"]["total_leads"] == 0


@pytest.mark.asyncio
async def test_team_empty(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/admin/stores", json={"nome_fantasia": "Metrics Store 2"}, headers=headers)
    store_id = created.json()["id"]
    res = await client.get(f"/metrics/team?store_id={store_id}&start=2026-01-01&end=2026-12-31", headers=headers)
    assert res.status_code == 200
    assert res.json()["rows"] == []


@pytest.mark.asyncio
async def test_dashboard_conta_classificados(client: AsyncClient) -> None:
    """O funil do dashboard inclui a etapa CLASSIFICADOS (S2.6)."""
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    wanted = ["RECEBIDOS", "CLASSIFICADOS", "QUALIFICADOS"]
    await client.post(
        "/admin/crm/templates", json={"name": "Tpl Classificados", "stages": wanted}, headers=headers
    )
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Classificados"}, headers=headers)).json()
    store_id = store["id"]
    await client.patch(f"/admin/stores/{store_id}", json={"crm_enabled": True}, headers=headers)

    # o clone usa o PRIMEIRO template do banco, então completamos o funil com o que faltar
    funnel = (await client.get(f"/crm/funnels?store_id={store_id}", headers=headers)).json()[0]
    existing = {s["name"] for s in funnel["stages"]}
    next_order = max(s["sort_order"] for s in funnel["stages"]) + 1
    for name in wanted:
        if name not in existing:
            await client.post(
                "/crm/stages",
                json={"funnel_id": funnel["id"], "name": name, "sort_order": next_order},
                headers=headers,
            )
            next_order += 1
    funnel = (await client.get(f"/crm/funnels?store_id={store_id}", headers=headers)).json()[0]
    stages = {s["name"]: s["id"] for s in funnel["stages"]}

    lead = (await client.post(
        "/crm/leads",
        json={
            "store_id": store_id,
            "stage_id": stages["RECEBIDOS"],
            "funil": "receptivo",
            "nome": "Lead Classificado",
            "telefone": "(11) 90000-0100",
            "cidade": "Belo Horizonte",
        },
        headers=headers,
    )).json()
    # o funil clonado pode ter etapas intermediárias com obrigatórios próprios;
    # preenchemos para que a movimentação até CLASSIFICADOS não seja barrada
    await client.patch(
        f"/crm/leads/{lead['id']}/agendamento",
        json={"data_agendamento": "2026-07-20", "hora_agendamento": "10:00"},
        headers=headers,
    )
    moved = await client.patch(
        f"/crm/leads/{lead['id']}/stage", json={"to_stage_id": stages["CLASSIFICADOS"]}, headers=headers
    )
    assert moved.status_code == 200, moved.text

    res = await client.get(
        f"/metrics/dashboard?store_id={store_id}&start=2026-01-01&end=2026-12-31", headers=headers
    )
    assert res.status_code == 200
    totals = res.json()["totals"]
    assert "classified_leads" in totals, "o funil precisa expor a etapa CLASSIFICADOS"
    assert totals["total_leads"] == 1
    assert totals["classified_leads"] == 1
