import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.orm import UserModel
from src.modules.stores.infrastructure.repository import (
    SqlAlchemyStoreAccessReader,
    SqlAlchemyStoreRepository,
    SqlAlchemyUserStoreAccessRepository,
)


async def _seed_user(session: AsyncSession) -> str:
    user_id = str(uuid.uuid4())
    session.add(UserModel(
        id=user_id, email=f"{user_id}@test.local", name="Test",
        role="client", parent_store_id=None, active=True, password_hash="hashed_test",
    ))
    await session.flush()
    return user_id


@pytest.fixture
def store_repo(session: AsyncSession) -> SqlAlchemyStoreRepository:
    return SqlAlchemyStoreRepository(session)


@pytest.fixture
def access_reader(session: AsyncSession) -> SqlAlchemyStoreAccessReader:
    return SqlAlchemyStoreAccessReader(session)


@pytest.fixture
def access_repo(session: AsyncSession) -> SqlAlchemyUserStoreAccessRepository:
    return SqlAlchemyUserStoreAccessRepository(session)


async def test_create_and_get_store(store_repo: SqlAlchemyStoreRepository) -> None:
    store = await store_repo.create({"nome_fantasia": "Loja Teste", "crm_enabled": True})
    assert store.nome_fantasia == "Loja Teste"
    assert store.crm_enabled is True
    assert store.active is True

    fetched = await store_repo.get_by_id(store.id)
    assert fetched is not None
    assert fetched.id == store.id


async def test_list_all_stores(store_repo: SqlAlchemyStoreRepository) -> None:
    await store_repo.create({"nome_fantasia": "Loja A"})
    await store_repo.create({"nome_fantasia": "Loja B"})
    stores = await store_repo.list_all()
    names = [s.nome_fantasia for s in stores]
    assert "Loja A" in names
    assert "Loja B" in names


async def test_update_store(store_repo: SqlAlchemyStoreRepository) -> None:
    store = await store_repo.create({"nome_fantasia": "Original"})
    updated = await store_repo.update(store.id, {"nome_fantasia": "Atualizado", "active": False})
    assert updated.nome_fantasia == "Atualizado"
    assert updated.active is False


async def test_get_and_set_role_labels(store_repo: SqlAlchemyStoreRepository) -> None:
    store = await store_repo.create({"nome_fantasia": "Loja Labels"})
    labels_before = await store_repo.get_role_labels(store.id)
    assert labels_before is None

    await store_repo.set_role_labels(store.id, {"sdr": "Pré-vendas", "vendedor": "Consultor"})
    labels_after = await store_repo.get_role_labels(store.id)
    assert isinstance(labels_after, dict)
    assert labels_after["sdr"] == "Pré-vendas"  # type: ignore[index]


async def test_store_access_reader(
    session: AsyncSession,
    store_repo: SqlAlchemyStoreRepository,
    access_repo: SqlAlchemyUserStoreAccessRepository,
    access_reader: SqlAlchemyStoreAccessReader,
) -> None:
    user_id = await _seed_user(session)
    store = await store_repo.create({"nome_fantasia": "Loja Acesso"})

    ids_before = await access_reader.store_ids_for_user(user_id)
    assert ids_before == []

    await access_repo.replace_links(user_id, [(store.id, False)])
    ids_after = await access_reader.store_ids_for_user(user_id)
    assert store.id in ids_after


async def test_replace_links_removes_old(
    session: AsyncSession,
    store_repo: SqlAlchemyStoreRepository,
    access_repo: SqlAlchemyUserStoreAccessRepository,
    access_reader: SqlAlchemyStoreAccessReader,
) -> None:
    user_id = await _seed_user(session)
    store1 = await store_repo.create({"nome_fantasia": "Loja 1"})
    store2 = await store_repo.create({"nome_fantasia": "Loja 2"})

    await access_repo.replace_links(user_id, [(store1.id, True)])
    await access_repo.replace_links(user_id, [(store2.id, False)])

    ids = await access_reader.store_ids_for_user(user_id)
    assert store1.id not in ids
    assert store2.id in ids
