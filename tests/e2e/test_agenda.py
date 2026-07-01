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
