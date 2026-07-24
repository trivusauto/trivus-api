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


async def test_flag_can_edit_others_leads_no_crud_de_equipe(client: AsyncClient) -> None:
    """Create aceita a flag, GET devolve e PATCH concede/retira (S3.2)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    loja = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Flag"}, headers=headers)).json()

    email = f"sdr_flag_{uuid.uuid4().hex[:8]}@example.com"
    created = await client.post(
        f"/stores/{loja['id']}/team",
        json={"email": email, "password": "demo123", "name": "SDR Flag", "shop_role": "sdr"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["can_edit_others_leads"] is False, "default é restrito"
    user_id = created.json()["id"]

    # com a flag ligada já na criação
    com_flag = await client.post(
        f"/stores/{loja['id']}/team",
        json={
            "email": f"sdr_flag2_{uuid.uuid4().hex[:8]}@example.com",
            "password": "demo123", "name": "SDR Com Flag", "shop_role": "sdr",
            "can_edit_others_leads": True,
        },
        headers=headers,
    )
    assert com_flag.status_code == 201, com_flag.text
    assert com_flag.json()["can_edit_others_leads"] is True

    # GET do team devolve a flag
    team = (await client.get(f"/stores/{loja['id']}/team", headers=headers)).json()
    assert {u["email"]: u["can_edit_others_leads"] for u in team}[email] is False

    # PATCH concede
    granted = await client.patch(
        f"/stores/{loja['id']}/team/{user_id}", json={"can_edit_others_leads": True}, headers=headers
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["can_edit_others_leads"] is True

    team = (await client.get(f"/stores/{loja['id']}/team", headers=headers)).json()
    assert {u["email"]: u["can_edit_others_leads"] for u in team}[email] is True


async def test_patch_flag_recusa_colaborador_de_outra_loja(client: AsyncClient) -> None:
    """Não dá para conceder a flag a alguém de outra loja (S3.2)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    loja_a = (await client.post("/admin/stores", json={"nome_fantasia": "Flag A"}, headers=headers)).json()
    loja_b = (await client.post("/admin/stores", json={"nome_fantasia": "Flag B"}, headers=headers)).json()

    membro_b = (await client.post(
        f"/stores/{loja_b['id']}/team",
        json={
            "email": f"sdr_b_{uuid.uuid4().hex[:8]}@example.com",
            "password": "demo123", "name": "SDR B", "shop_role": "sdr",
        },
        headers=headers,
    )).json()

    res = await client.patch(
        f"/stores/{loja_a['id']}/team/{membro_b['id']}",
        json={"can_edit_others_leads": True},
        headers=headers,
    )
    assert res.status_code == 404


async def test_gerente_cria_equipe_da_propria_loja(client: AsyncClient) -> None:
    """POST /stores/{id}/team liberado para gerente da própria loja; 403 em outra (S3.7)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    minha = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Ger Cria"}, headers=headers)).json()
    outra = (await client.post("/admin/stores", json={"nome_fantasia": "Loja Ger Outra"}, headers=headers)).json()

    email_ger = f"gerente_cria_{uuid.uuid4().hex[:8]}@example.com"
    created = await client.post(
        f"/stores/{minha['id']}/team",
        json={"email": email_ger, "password": "demo123", "name": "Gerente", "shop_role": "gerente"},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    login = await client.post("/auth/login", json={"email": email_ger, "password": "demo123"})
    ger = {"Authorization": f"Bearer {login.json()['access_token']}"}

    novo = await client.post(
        f"/stores/{minha['id']}/team",
        json={
            "email": f"sdr_do_gerente_{uuid.uuid4().hex[:8]}@example.com",
            "password": "demo123", "name": "SDR do Gerente", "shop_role": "sdr",
        },
        headers=ger,
    )
    assert novo.status_code == 201, novo.text

    alheia = await client.post(
        f"/stores/{outra['id']}/team",
        json={
            "email": f"sdr_alheio_{uuid.uuid4().hex[:8]}@example.com",
            "password": "demo123", "name": "SDR Alheio", "shop_role": "sdr",
        },
        headers=ger,
    )
    assert alheia.status_code == 403


async def test_sdr_nao_cria_equipe(client: AsyncClient) -> None:
    """shop_user comum continua sem poder criar colaborador (S3.7)."""
    headers = {"Authorization": f"Bearer {await _admin_token(client)}"}
    loja = (await client.post("/admin/stores", json={"nome_fantasia": "Loja SDR Cria"}, headers=headers)).json()

    email_sdr = f"sdr_nocreate_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        f"/stores/{loja['id']}/team",
        json={"email": email_sdr, "password": "demo123", "name": "SDR", "shop_role": "sdr"},
        headers=headers,
    )
    login = await client.post("/auth/login", json={"email": email_sdr, "password": "demo123"})
    sdr = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.post(
        f"/stores/{loja['id']}/team",
        json={
            "email": f"x_{uuid.uuid4().hex[:8]}@example.com",
            "password": "demo123", "name": "X", "shop_role": "sdr",
        },
        headers=sdr,
    )
    assert res.status_code == 403
