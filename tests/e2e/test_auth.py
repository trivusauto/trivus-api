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
