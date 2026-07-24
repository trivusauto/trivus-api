from pydantic import BaseModel, EmailStr


class ManagerRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class CreateStoreRequest(BaseModel):
    nome_fantasia: str
    razao_social: str | None = None
    cnpj: str | None = None
    # Gerentes criados junto com a loja (opcional; o front exige ao menos 1).
    managers: list[ManagerRequest] = []


class StoreResponse(BaseModel):
    id: str
    nome_fantasia: str
    crm_enabled: bool
    active: bool
