from pydantic import BaseModel


class CreateStoreRequest(BaseModel):
    nome_fantasia: str
    razao_social: str | None = None
    cnpj: str | None = None


class StoreResponse(BaseModel):
    id: str
    nome_fantasia: str
    crm_enabled: bool
    active: bool
