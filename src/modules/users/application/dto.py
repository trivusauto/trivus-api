from dataclasses import dataclass, field


@dataclass
class CreateTeamUserInput:
    email: str
    password: str
    name: str
    store_id: str
    shop_role: str | None = None
    menu_permissions: list[str] = field(default_factory=list)
    can_see_unassigned_leads: bool = False
    can_edit_others_leads: bool = False
