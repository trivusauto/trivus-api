import pytest


async def _admin(client):  # type: ignore[no-untyped-def]
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_list_update_campaign(client) -> None:  # type: ignore[no-untyped-def]
    headers = await _admin(client)
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Loja MKT"}, headers=headers)).json()

    created = await client.post("/campaigns", json={
        "store_id": store["id"], "name": "Carro Popular Julho",
        "started_at": "2026-07-01", "budget": 10000, "link_code": "carro-popular-julho",
    }, headers=headers)
    assert created.status_code == 201
    camp = created.json()
    assert camp["budget"] == 10000.0 and camp["ended_at"] is None

    listed = await client.get(f"/campaigns?store_id={store['id']}", headers=headers)
    assert any(c["name"] == "Carro Popular Julho" for c in listed.json())

    updated = await client.patch(f"/campaigns/{camp['id']}", json={"ended_at": "2026-07-31"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["ended_at"] == "2026-07-31"
