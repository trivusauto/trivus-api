import pytest
from httpx import AsyncClient


async def _admin_token(client: AsyncClient) -> str:
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    return str(res.json()["access_token"])


@pytest.mark.asyncio
async def test_create_and_list_goal(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Goals Store"}, headers=headers)).json()
    store_id = store["id"]
    res = await client.post(
        "/admin/goals",
        json={"store_id": store_id, "year": 2026, "month": 6, "origin": "receptivo", "conversions_quantity": 10},
        headers=headers,
    )
    assert res.status_code == 201
    listed = await client.get(f"/goals?store_id={store_id}&year=2026&month=6", headers=headers)
    assert listed.status_code == 200
    assert any(g["conversions_quantity"] == 10 for g in listed.json())


@pytest.mark.asyncio
async def test_upsert_and_read_classified_quantity(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Classified Store"}, headers=headers)).json()
    store_id = store["id"]

    created = await client.post(
        "/admin/goals",
        json={
            "store_id": store_id,
            "year": 2026,
            "month": 7,
            "origin": "receptivo",
            "leads_quantity": 90,
            "classified_quantity": 25,
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["classified_quantity"] == 25

    listed = await client.get(f"/goals?store_id={store_id}&year=2026&month=7", headers=headers)
    assert listed.status_code == 200
    goal = next(g for g in listed.json() if g["origin"] == "receptivo")
    assert goal["classified_quantity"] == 25


@pytest.mark.asyncio
async def test_classified_quantity_rejects_negative(client: AsyncClient) -> None:
    token = await _admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    store = (await client.post("/admin/stores", json={"nome_fantasia": "Classified Neg"}, headers=headers)).json()
    res = await client.post(
        "/admin/goals",
        json={
            "store_id": store["id"],
            "year": 2026,
            "month": 7,
            "origin": "receptivo",
            "classified_quantity": -5,
        },
        headers=headers,
    )
    assert res.status_code == 422
