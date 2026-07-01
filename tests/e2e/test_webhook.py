import uuid
import pytest
from httpx import AsyncClient


async def _admin(client: AsyncClient) -> dict[str, str]:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_group_skipped(client: AsyncClient) -> None:
    token = uuid.uuid4().hex
    headers = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja WH"}, headers=headers)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"webhook_token": token, "zapi_webhook_enabled": True}, headers=headers)
    res = await client.post(f"/webhook/zapi/{token}", json={"isGroup": True})
    assert res.status_code == 200
    assert res.json()["skipped"] in ("group", "disabled")
