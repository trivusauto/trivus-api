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


@pytest.mark.asyncio
async def test_change_password_wrong_current(client) -> None:  # type: ignore[misc]
    login_res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    token = login_res.json()["access_token"]
    res = await client.post(
        "/auth/change-password",
        json={"current_password": "wrong", "new_password": "newpass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_change_password_and_relogin(client) -> None:  # type: ignore[misc]
    login_res = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "admin123"})
    token = login_res.json()["access_token"]

    # change password
    change_res = await client.post(
        "/auth/change-password",
        json={"current_password": "admin123", "new_password": "newpass456"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_res.status_code == 204

    # re-login with new password
    new_login = await client.post("/auth/login", json={"email": "admin@trivus.local", "password": "newpass456"})
    assert new_login.status_code == 200

    # restore original password
    new_token = new_login.json()["access_token"]
    restore = await client.post(
        "/auth/change-password",
        json={"current_password": "newpass456", "new_password": "admin123"},
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert restore.status_code == 204
