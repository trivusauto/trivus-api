import uuid

import pytest


async def _admin(client):  # type: ignore[no-untyped-def]
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_full_ecosystem_flow(client) -> None:  # type: ignore[no-untyped-def]
    h = await _admin(client)
    suffix = uuid.uuid4().hex[:6]

    svc = (await client.post("/admin/services", json={
        "key": f"crm_completo_{suffix}", "name": "CRM Completo", "type": "software",
        "what_it_is": "Kanban de leads", "upsell_pitch": "Organize seus leads",
        "feature_keys": ["crm.kanban", "agenda"]}, headers=h)).json()
    plan = (await client.post("/admin/plans", json={
        "key": f"pro_{suffix}", "name": "Pro", "service_keys": [svc["key"]]}, headers=h)).json()
    company = (await client.post("/admin/companies", json={"name": f"Grupo {suffix}"}, headers=h)).json()
    store = (await client.post("/admin/stores", json={"nome_fantasia": f"Loja {suffix}"}, headers=h)).json()
    linked = await client.patch(f"/admin/stores/{store['id']}", json={"company_id": company["id"]}, headers=h)
    assert linked.status_code == 200

    sub = await client.post("/admin/subscriptions", json={
        "company_id": company["id"], "plan_id": plan["id"], "status": "active"}, headers=h)
    assert sub.status_code == 201

    # antes de ligar o serviço na loja: nada desbloqueado
    ent = (await client.get(f"/ecosystem/my-entitlements?store_id={store['id']}", headers=h)).json()
    assert ent["feature_keys"] == []

    # liga o serviço na loja → keys aparecem
    toggled = await client.put(f"/admin/stores/{store['id']}/services",
                               json={"service_key": svc["key"], "enabled": True}, headers=h)
    assert toggled.status_code == 200
    ent = (await client.get(f"/ecosystem/my-entitlements?store_id={store['id']}", headers=h)).json()
    assert set(ent["feature_keys"]) == {"agenda", "crm.kanban"}

    # catálogo mostra o serviço desbloqueado
    cat = (await client.get(f"/ecosystem/services?store_id={store['id']}", headers=h)).json()
    mine = next(s for s in cat["services"] if s["key"] == svc["key"])
    assert mine["unlocked"] is True

    # interesse (upsell) registrado e visível na fila do admin
    res = await client.post("/ecosystem/interests",
                            json={"store_id": store["id"], "service_key": svc["key"]}, headers=h)
    assert res.status_code == 201
    interests = (await client.get("/admin/interests?status=novo", headers=h)).json()
    assert any(i["store_id"] == store["id"] for i in interests)


@pytest.mark.asyncio
async def test_gate_blocks_store_without_service(client) -> None:  # type: ignore[no-untyped-def]
    """Loja com empresa+assinatura mas SEM o serviço de agenda → 403 feature_locked
    quando um usuário não-admin acessa (admin bypassa — E7)."""
    h = await _admin(client)
    suffix = uuid.uuid4().hex[:6]

    company = (await client.post("/admin/companies", json={"name": f"G2 {suffix}"}, headers=h)).json()
    store = (await client.post("/admin/stores", json={"nome_fantasia": f"L2 {suffix}"}, headers=h)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"company_id": company["id"]}, headers=h)
    plan = (await client.post("/admin/plans", json={"key": f"vazio_{suffix}", "name": "Vazio"}, headers=h)).json()
    await client.post("/admin/subscriptions", json={
        "company_id": company["id"], "plan_id": plan["id"], "status": "active"}, headers=h)

    # cria um usuário client vinculado (não-admin) e loga
    email = f"dono_{suffix}@loja.com"
    await client.post("/admin/users", json={"email": email, "password": "segredo1", "name": "Dono"}, headers=h)
    login = await client.post("/auth/login", json={"email": email, "password": "segredo1"})
    dono_h = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.get(f"/agenda?store_id={store['id']}", headers=dono_h)
    assert res.status_code == 403
    assert res.json()["error"] == "feature_locked"
    assert res.json()["feature_key"] == "agenda"

    # admin bypassa (E7)
    res_admin = await client.get(f"/agenda?store_id={store['id']}", headers=h)
    assert res_admin.status_code == 200


@pytest.mark.asyncio
async def test_billing_endpoint_disabled_by_flag(client) -> None:  # type: ignore[no-untyped-def]
    res = await client.post("/integrations/billing/events",
                            json={"subscription_id": "x", "event_type": "payment_confirmed"},
                            headers={"x-billing-token": "dev-billing-token"})
    assert res.status_code == 409          # BILLING_GATEWAY_ENABLED=false


@pytest.mark.asyncio
async def test_legacy_store_not_gated(client) -> None:  # type: ignore[no-untyped-def]
    """E6: loja sem empresa vinculada continua com acesso total (modo legado pré-ETL)."""
    h = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Legada"}, headers=h)).json()
    ent = (await client.get(f"/ecosystem/my-entitlements?store_id={store['id']}", headers=h)).json()
    assert "agenda" in ent["feature_keys"] and "crm.kanban" in ent["feature_keys"]


@pytest.mark.asyncio
async def test_loja_sem_empresa_opera_normalmente(client) -> None:  # type: ignore[no-untyped-def]
    """S3.8 (Opção A): loja sem empresa acessa CRM, métricas e campanhas."""
    h = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Sem Empresa"}, headers=h)).json()
    sid = store["id"]

    assert (await client.get(f"/crm/leads?store_id={sid}", headers=h)).status_code == 200
    assert (await client.get(
        f"/metrics/dashboard?store_id={sid}&start=2026-01-01&end=2026-12-31", headers=h
    )).status_code == 200
    assert (await client.get(f"/campaigns?store_id={sid}", headers=h)).status_code == 200


@pytest.mark.asyncio
async def test_loja_sem_empresa_liga_servico(client) -> None:  # type: ignore[no-untyped-def]
    """S3.8: ligar serviço numa loja sem empresa não lança mais o erro de modo legado."""
    h = await _admin(client)
    suffix = uuid.uuid4().hex[:6]
    svc = (await client.post("/admin/services", json={
        "key": f"svc_sem_empresa_{suffix}", "name": "Serviço X", "type": "software",
        "what_it_is": "x", "upsell_pitch": "x", "feature_keys": ["goals"]}, headers=h)).json()
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Sem Empresa Toggle"}, headers=h)).json()

    res = await client.put(f"/admin/stores/{store['id']}/services",
                           json={"service_key": svc["key"], "enabled": True}, headers=h)
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_empresa_suspensa_continua_bloqueada(client) -> None:  # type: ignore[no-untyped-def]
    """S3.8: liberar loja SEM empresa não afrouxa loja COM empresa suspensa."""
    h = await _admin(client)
    suffix = uuid.uuid4().hex[:6]

    svc = (await client.post("/admin/services", json={
        "key": f"svc_susp_{suffix}", "name": "CRM", "type": "software",
        "what_it_is": "x", "upsell_pitch": "x", "feature_keys": ["crm.kanban"]}, headers=h)).json()
    plan = (await client.post("/admin/plans", json={
        "key": f"plan_susp_{suffix}", "name": "Plano", "service_keys": [svc["key"]]}, headers=h)).json()
    company = (await client.post("/admin/companies", json={"name": f"Suspensa {suffix}"}, headers=h)).json()
    store = (await client.post("/admin/stores", json={"nome_fantasia": f"Loja Susp {suffix}"}, headers=h)).json()
    await client.patch(f"/admin/stores/{store['id']}", json={"company_id": company["id"]}, headers=h)
    await client.post("/admin/subscriptions", json={
        "company_id": company["id"], "plan_id": plan["id"], "status": "suspended"}, headers=h)

    ent = (await client.get(f"/ecosystem/my-entitlements?store_id={store['id']}", headers=h)).json()
    assert ent["feature_keys"] == [], "assinatura suspensa continua bloqueando tudo"
