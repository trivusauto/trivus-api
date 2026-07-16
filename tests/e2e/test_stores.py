from uuid import uuid4

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


async def test_stores_mine_lists_linked_stores(client: AsyncClient) -> None:
    """Dono (role client) vê via /stores/mine apenas as lojas vinculadas em user_store_access."""
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    email = f"dono.{uuid4().hex[:8]}@trivus.com.br"  # único por execução (banco pode persistir entre runs)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Mine"}, headers=headers)).json()
    owner = (await client.post(
        "/admin/users",
        json={"email": email, "password": "segredo1", "name": "Dono Mine"},
        headers=headers,
    )).json()
    await client.put(
        f"/admin/users/{owner['id']}/stores",
        json={"store_ids": [store["id"]], "owner_store_ids": [store["id"]]},
        headers=headers,
    )

    login = await client.post("/auth/login", json={"email": email, "password": "segredo1"})
    owner_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    mine = await client.get("/stores/mine", headers=owner_headers)
    assert mine.status_code == 200
    assert [s["id"] for s in mine.json()] == [store["id"]]

    # sem vínculo → lista vazia (admin não tem user_store_access)
    admin_mine = await client.get("/stores/mine", headers=headers)
    assert admin_mine.status_code == 200
    assert admin_mine.json() == []
