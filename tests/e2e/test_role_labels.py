from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


async def test_get_and_set_role_labels(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    store = await client.post("/admin/stores", json={"nome_fantasia": "Loja Labels E2E"}, headers=headers)
    store_id = store.json()["id"]

    patched = await client.patch(f"/admin/stores/{store_id}/role-labels", json={"sdr": "Pré-vendas"}, headers=headers)
    assert patched.status_code == 200
    data = patched.json()
    assert data["sdr"] == "Pré-vendas"
    assert data["vendedor"] == "Vendedor"

    fetched = await client.get(f"/admin/stores/{store_id}/role-labels", headers=headers)
    assert fetched.json()["sdr"] == "Pré-vendas"
