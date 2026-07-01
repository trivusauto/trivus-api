from src.modules.auth.domain.entities import User


def test_user_is_admin() -> None:
    admin = User(id="1", email="a@b.com", name="A", role="admin", parent_store_id=None, active=True, password_hash="h")
    client = User(id="2", email="c@b.com", name="C", role="client", parent_store_id=None, active=True, password_hash="h")
    assert admin.is_admin() is True
    assert client.is_admin() is False
