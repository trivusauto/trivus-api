from typing import Literal
from pydantic import BaseModel

_STATUSES = {"a_fazer", "em_andamento", "concluido"}


class CreateActionPlanRequest(BaseModel):
    store_id: str
    title: str
    description: str | None = None
    status: Literal["a_fazer", "em_andamento", "concluido"] = "a_fazer"


class UpdateActionPlanRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: Literal["a_fazer", "em_andamento", "concluido"] | None = None


class UpdateStatusRequest(BaseModel):
    status: Literal["a_fazer", "em_andamento", "concluido"]
