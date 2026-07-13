import pytest


async def _admin(client):  # type: ignore[no-untyped-def]
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_requires_admin(client) -> None:  # type: ignore[no-untyped-def]
    res = await client.get("/admin/bulk-sends")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_list_and_logs(client) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin(client)
    created = await client.post("/admin/bulk-sends", json={
        "title": "Campanha Teste", "message_template": "oi",
        "phones": ["11999999999", "5511988887777", "11999999999"],
    }, headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["stats"]["total"] == 2 and body["stats"]["duplicated"] == 1

    listed = await client.get("/admin/bulk-sends", headers=headers)
    assert any(s["id"] == body["id"] for s in listed.json())

    logs = await client.get(f"/admin/bulk-sends/{body['id']}/logs", headers=headers)
    assert logs.status_code == 200
    assert len(logs.json()) == 2
    assert all(c["status"] == "pending" for c in logs.json())


@pytest.mark.asyncio
async def test_n8n_status_callback(client) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin(client)
    created = (await client.post("/admin/bulk-sends", json={
        "message_template": "oi", "phones": ["11988887777"],
    }, headers=headers)).json()
    contact = (await client.get(f"/admin/bulk-sends/{created['id']}/logs", headers=headers)).json()[0]

    unauthorized = await client.patch(f"/integrations/bulk-send/contacts/{contact['id']}/status",
                                      json={"status": "sent"}, headers={"x-n8n-token": "wrong"})
    assert unauthorized.status_code == 401

    ok = await client.patch(f"/integrations/bulk-send/contacts/{contact['id']}/status",
                            json={"status": "sent"}, headers={"x-n8n-token": "dev-n8n-token"})
    assert ok.status_code == 200

    logs = (await client.get(f"/admin/bulk-sends/{created['id']}/logs", headers=headers)).json()
    assert logs[0]["status"] == "sent"
