import uuid

from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository


async def test_create_and_list_portal(session) -> None:  # type: ignore[no-untyped-def]
    repo = SqlAlchemyUserRepository(session)
    email = f"{uuid.uuid4()}@loja.com"
    await repo.create({"email": email, "name": "Dono", "role": "client", "password_hash": "$argon2id$x", "active": True})
    portal = await repo.list_portal()
    assert any(u.email == email for u in portal)
