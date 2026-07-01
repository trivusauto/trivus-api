import pytest


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client) -> None:  # type: ignore[misc]
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_ok(client) -> None:  # type: ignore[misc]
    res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_me_without_token(client) -> None:  # type: ignore[misc]
    res = await client.get("/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client) -> None:  # type: ignore[misc]
    login_res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    token = login_res.json()["access_token"]
    res = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "admin@trivus.local"
