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


async def test_gerente_le_equipe_da_propria_loja(client: AsyncClient) -> None:
    """GET /stores/{id}/team liberado para gerente da própria loja; 403 em outra (S2.11)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    minha = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Gerente"}, headers=headers)).json()
    outra = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Alheia"}, headers=headers)).json()

    senha = "demo123"
    email = f"gerente_{uuid.uuid4().hex[:8]}@example.com"
    created = await client.post(
        f"/stores/{minha['id']}/team",
        json={"email": email, "password": senha, "name": "Gerente Um", "shop_role": "gerente"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    login = await client.post("/auth/login", json={"email": email, "password": senha})
    assert login.status_code == 200, login.text
    ger_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    propria = await client.get(f"/stores/{minha['id']}/team", headers=ger_headers)
    assert propria.status_code == 200, propria.text
    assert any(u["email"] == email for u in propria.json())

    alheia = await client.get(f"/stores/{outra['id']}/team", headers=ger_headers)
    assert alheia.status_code == 403


async def test_sdr_nao_le_equipe(client: AsyncClient) -> None:
    """shop_user comum (não gerente) continua bloqueado (S2.11)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    loja = (await client.post("/admin/stores", json={"nome_fantasia": "Loja SDR"}, headers=headers)).json()

    senha = "demo123"
    email = f"sdr_{uuid.uuid4().hex[:8]}@example.com"
    created = await client.post(
        f"/stores/{loja['id']}/team",
        json={"email": email, "password": senha, "name": "SDR Um", "shop_role": "sdr"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    login = await client.post("/auth/login", json={"email": email, "password": senha})
    sdr_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.get(f"/stores/{loja['id']}/team", headers=sdr_headers)
    assert res.status_code == 403
