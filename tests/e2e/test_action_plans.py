import pytest
from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


@pytest.mark.asyncio
async def test_action_plan_lifecycle(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    store = (await client.post("/admin/stores", json={"nome_fantasia": "AP Store"}, headers=headers)).json()
    store_id = store["id"]
    created = await client.post(
        "/admin/action-plans",
        json={"store_id": store_id, "title": "Aumentar conversões"},
        headers=headers,
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]
    patched = await client.patch(f"/action-plans/{plan_id}/status", json={"status": "em_andamento"}, headers=headers)
    assert patched.status_code == 200
    assert patched.json()["status"] == "em_andamento"
    listed = await client.get(f"/action-plans?store_id={store_id}", headers=headers)
    assert any(p["title"] == "Aumentar conversões" for p in listed.json())


@pytest.mark.asyncio
async def test_plan_com_prazo_responsaveis_e_steps(client: AsyncClient) -> None:
    """Plano com due_date, responsáveis (nomes no list) e CRUD de etapas + cascade (S5.2)."""
    import uuid
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Roadmap Store"}, headers=headers)).json()
    sid = store["id"]

    email = f"resp_{uuid.uuid4().hex[:8]}@example.com"
    resp = (await client.post(f"/stores/{sid}/team", json={
        "email": email, "password": "demo123", "name": "Responsável Um", "shop_role": "gerente",
    }, headers=headers)).json()

    plan = (await client.post("/admin/action-plans", json={
        "store_id": sid, "title": "Roadmap Q3",
        "due_date": "2026-09-30", "responsible_ids": [resp["id"]],
    }, headers=headers)).json()
    plan_id = plan["id"]
    assert plan["due_date"] == "2026-09-30"

    # cria duas etapas fora de ordem; o list volta ordenado por sort_order
    s2 = (await client.post(f"/action-plans/{plan_id}/steps", json={
        "title": "Etapa 2", "due_date": "2026-08-15", "sort_order": 2,
    }, headers=headers)).json()
    await client.post(f"/action-plans/{plan_id}/steps", json={
        "title": "Etapa 1", "sort_order": 1,
    }, headers=headers)

    steps = (await client.get(f"/action-plans/{plan_id}/steps", headers=headers)).json()
    assert [s["title"] for s in steps] == ["Etapa 1", "Etapa 2"]

    # concluir uma etapa
    done = await client.patch(f"/action-plans/{plan_id}/steps/{s2['id']}", json={"done": True}, headers=headers)
    assert done.status_code == 200 and done.json()["done"] is True

    # o list de planos inclui prazo, nomes dos responsáveis e steps
    listed = (await client.get(f"/action-plans?store_id={sid}", headers=headers)).json()
    row = next(p for p in listed if p["id"] == plan_id)
    assert row["responsible_names"] == ["Responsável Um"]
    assert row["due_date"] == "2026-09-30"
    assert len(row["steps"]) == 2

    # remover uma etapa
    rm = await client.delete(f"/action-plans/{plan_id}/steps/{s2['id']}", headers=headers)
    assert rm.status_code == 204
    assert len((await client.get(f"/action-plans/{plan_id}/steps", headers=headers)).json()) == 1

    # apagar o plano leva as etapas junto (CASCADE)
    await client.delete(f"/admin/action-plans/{plan_id}", headers=headers)
    orphan = await client.get(f"/action-plans/{plan_id}/steps", headers=headers)
    assert orphan.status_code == 404


@pytest.mark.asyncio
async def test_step_em_plano_inexistente_404(client: AsyncClient) -> None:
    import uuid
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    res = await client.post(f"/action-plans/{uuid.uuid4()}/steps", json={"title": "X"}, headers=headers)
    assert res.status_code == 404
