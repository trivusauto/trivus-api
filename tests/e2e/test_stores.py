from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


async def test_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/admin/stores")
    assert res.status_code == 401


async def test_create_and_list(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/admin/stores", json={"nome_fantasia": "Loja E2E"}, headers=headers)
    assert created.status_code == 201
    listed = await client.get("/admin/stores", headers=headers)
    assert any(s["nome_fantasia"] == "Loja E2E" for s in listed.json())
