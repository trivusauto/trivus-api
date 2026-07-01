import uuid

from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


async def test_create_and_list_portal_user(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    email = f"portal_{uuid.uuid4()}@loja.com"
    created = await client.post("/admin/users", json={"email": email, "password": "segredo1", "name": "Dono"}, headers=headers)
    assert created.status_code == 201
    listed = await client.get("/admin/users", headers=headers)
    assert any(u["email"] == email for u in listed.json())
