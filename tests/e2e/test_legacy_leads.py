import pytest
from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


@pytest.mark.asyncio
async def test_create_and_list_legacy_lead(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Legacy Store"}, headers=headers)).json()
    store_id = store["id"]
    res = await client.post("/leads", json={"store_id": store_id, "name": "João Silva", "origin": "receptivo"}, headers=headers)
    assert res.status_code == 201
    listed = await client.get(f"/leads?store_id={store_id}", headers=headers)
    assert listed.status_code == 200
    assert any(item["name"] == "João Silva" for item in listed.json())
