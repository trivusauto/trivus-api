"""S4.1 — validação de múltiplas lojas (`?store_ids=a&store_ids=b`)."""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.orm import UserModel
from src.modules.stores.infrastructure.orm import StoreModel
from src.modules.stores.infrastructure.repository import SqlAlchemyUserStoreAccessRepository
from src.shared.domain.errors import ForbiddenError
from src.shared.interface.auth_deps import CurrentUser
from src.shared.interface.store_access import require_store_ids_access


async def _store(session: AsyncSession, nome: str) -> str:
    sid = str(uuid.uuid4())
    session.add(StoreModel(id=sid, nome_fantasia=nome, active=True))
    await session.flush()
    return sid


async def _client_user(session: AsyncSession, store_ids: list[str]) -> CurrentUser:
    uid = str(uuid.uuid4())
    session.add(UserModel(
        id=uid, email=f"{uid}@test.local", name="Dono", role="client",
        parent_store_id=None, active=True, password_hash="x",
    ))
    await session.flush()
    await SqlAlchemyUserStoreAccessRepository(session).replace_links(
        uid, [(sid, True) for sid in store_ids]
    )
    return CurrentUser(user_id=uid, role="client", parent_store_id=None)


@pytest.mark.asyncio
async def test_vazio_devolve_todas_as_lojas_acessiveis(session: AsyncSession) -> None:
    a = await _store(session, "Loja A")
    b = await _store(session, "Loja B")
    user = await _client_user(session, [a, b])

    out = await require_store_ids_access(store_ids=[], user=user, session=session)
    assert set(out) == {a, b}


@pytest.mark.asyncio
async def test_subconjunto_valido_passa(session: AsyncSession) -> None:
    a = await _store(session, "Loja A")
    b = await _store(session, "Loja B")
    user = await _client_user(session, [a, b])

    out = await require_store_ids_access(store_ids=[a], user=user, session=session)
    assert out == [a]


@pytest.mark.asyncio
async def test_loja_fora_do_escopo_derruba_com_403(session: AsyncSession) -> None:
    a = await _store(session, "Loja A")
    alheia = await _store(session, "Loja Alheia")
    user = await _client_user(session, [a])

    with pytest.raises(ForbiddenError):
        await require_store_ids_access(store_ids=[a, alheia], user=user, session=session)


@pytest.mark.asyncio
async def test_ids_repetidos_sao_deduplicados(session: AsyncSession) -> None:
    a = await _store(session, "Loja A")
    user = await _client_user(session, [a])

    out = await require_store_ids_access(store_ids=[a, a], user=user, session=session)
    assert out == [a]


@pytest.mark.asyncio
async def test_shop_user_fica_restrito_a_propria_loja(session: AsyncSession) -> None:
    a = await _store(session, "Loja A")
    alheia = await _store(session, "Loja Alheia")
    user = CurrentUser(user_id=str(uuid.uuid4()), role="shop_user", parent_store_id=a)

    assert await require_store_ids_access(store_ids=[], user=user, session=session) == [a]
    with pytest.raises(ForbiddenError):
        await require_store_ids_access(store_ids=[alheia], user=user, session=session)
