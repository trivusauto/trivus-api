from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    parent_store_id: str | None


class LoginResponse(BaseModel):
    access_token: str
    user: UserResponse
