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


async def test_cria_loja_com_gerentes(client: AsyncClient) -> None:
    """POST /admin/stores aceita managers[] e cria todos na mesma sessão (S3.6)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    e1 = f"ger1_{uuid4().hex[:8]}@example.com"
    e2 = f"ger2_{uuid4().hex[:8]}@example.com"

    created = await client.post(
        "/admin/stores",
        json={
            "nome_fantasia": "Loja Com Gerentes",
            "managers": [
                {"email": e1, "password": "demo123", "name": "Gerente Um"},
                {"email": e2, "password": "demo123", "name": "Gerente Dois"},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    store_id = created.json()["id"]

    team = (await client.get(f"/stores/{store_id}/team", headers=headers)).json()
    por_email = {u["email"]: u for u in team}
    assert set(por_email) == {e1, e2}
    assert all(u["shop_role"] == "gerente" for u in team)

    # os gerentes conseguem entrar
    login = await client.post("/auth/login", json={"email": e1, "password": "demo123"})
    assert login.status_code == 200, login.text


async def test_cria_loja_sem_managers_continua_funcionando(client: AsyncClient) -> None:
    """O campo é opcional — compatibilidade com o fluxo atual (S3.6)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    created = await client.post("/admin/stores", json={"nome_fantasia": "Loja Sem Gerente"}, headers=headers)
    assert created.status_code == 201, created.text
    team = (await client.get(f"/stores/{created.json()['id']}/team", headers=headers)).json()
    assert team == []


async def test_gerente_duplicado_desfaz_a_loja(client: AsyncClient) -> None:
    """Se um gerente falha, a loja inteira é revertida (mesma transação) (S3.6)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    email = f"dup_{uuid4().hex[:8]}@example.com"
    nome_loja = f"Loja Atomica {uuid4().hex[:6]}"

    res = await client.post(
        "/admin/stores",
        json={
            "nome_fantasia": nome_loja,
            "managers": [
                {"email": email, "password": "demo123", "name": "G1"},
                {"email": email, "password": "demo123", "name": "G2 duplicado"},
            ],
        },
        headers=headers,
    )
    assert res.status_code >= 400, "e-mail duplicado deve falhar"

    lojas = (await client.get("/admin/stores", headers=headers)).json()
    assert all(s["nome_fantasia"] != nome_loja for s in lojas), "a loja não pode ter sobrado"
