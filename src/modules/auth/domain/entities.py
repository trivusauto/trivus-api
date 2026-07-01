from dataclasses import dataclass, field


@dataclass
class User:
    id: str
    email: str
    name: str | None
    role: str  # admin | client | shop_user
    parent_store_id: str | None
    active: bool
    password_hash: str | None
    shop_role: str | None = None
    menu_permissions: list[str] = field(default_factory=list)
    can_see_unassigned_leads: bool = False

    def is_admin(self) -> bool:
        return self.role == "admin"
