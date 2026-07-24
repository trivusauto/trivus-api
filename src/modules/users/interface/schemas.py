from pydantic import BaseModel, EmailStr


class CreatePortalUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class CreateTeamUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    shop_role: str | None = None
    menu_permissions: list[str] = []
    can_see_unassigned_leads: bool = False
    can_edit_others_leads: bool = False


class UpdateTeamUserRequest(BaseModel):
    can_edit_others_leads: bool


class AssignStoresRequest(BaseModel):
    store_ids: list[str]
    owner_store_ids: list[str] = []


class PortalUserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    active: bool
    shop_role: str | None = None
    can_edit_others_leads: bool = False
