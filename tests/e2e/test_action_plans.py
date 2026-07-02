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
