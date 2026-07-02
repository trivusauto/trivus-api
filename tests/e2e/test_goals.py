import pytest
from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


@pytest.mark.asyncio
async def test_create_and_list_goal(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Goals Store"}, headers=headers)).json()
    store_id = store["id"]
    res = await client.post(
        "/admin/goals",
        json={"store_id": store_id, "year": 2026, "month": 6, "origin": "receptivo", "conversions_quantity": 10},
        headers=headers,
    )
    assert res.status_code == 201
    listed = await client.get(f"/goals?store_id={store_id}&year=2026&month=6", headers=headers)
    assert listed.status_code == 200
    assert any(g["conversions_quantity"] == 10 for g in listed.json())
