from dataclasses import dataclass


@dataclass
class User:
    id: str
    email: str
    name: str | None
    role: str  # admin | client | shop_user
    parent_store_id: str | None
    active: bool
    password_hash: str | None

    def is_admin(self) -> bool:
        return self.role == "admin"
