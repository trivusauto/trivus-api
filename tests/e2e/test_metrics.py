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
