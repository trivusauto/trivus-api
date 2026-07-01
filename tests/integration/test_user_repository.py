import uuid
import pytest
from src.modules.auth.infrastructure.orm import UserModel
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository


@pytest.mark.asyncio
async def test_get_by_email_and_update_password(session) -> None:  # type: ignore[misc]
    uid = str(uuid.uuid4())
    session.add(UserModel(id=uid, email=f"{uid}@t.com", name="T", role="admin", active=True, password_hash="hashed_x"))
    await session.flush()

    repo = SqlAlchemyUserRepository(session)
    found = await repo.get_by_email(f"{uid}@t.com")
    assert found is not None and found.id == uid

    await repo.update_password(uid, "$argon2id$novo")
    reloaded = await repo.get_by_id(uid)
    assert reloaded is not None and reloaded.password_hash == "$argon2id$novo"
