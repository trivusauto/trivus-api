from src.modules.auth.infrastructure.password_hasher import Argon2PasswordHasher

h = Argon2PasswordHasher()


def test_hash_and_verify() -> None:
    hashed = h.hash("s3nha")
    assert hashed.startswith("$argon2")
    assert h.verify("s3nha", hashed) is True
    assert h.verify("errada", hashed) is False


def test_legacy_hash_accepted() -> None:
    assert h.verify("minhasenha", "hashed_minhasenha") is True
    assert h.verify("x", "hashed_y") is False


def test_needs_rehash() -> None:
    assert h.needs_rehash("hashed_abc") is True
    assert h.needs_rehash(h.hash("x")) is False


def test_empty_hash() -> None:
    assert h.verify("x", None) is False
