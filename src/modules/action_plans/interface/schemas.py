from typing import Literal
from pydantic import BaseModel

_STATUSES = {"a_fazer", "em_andamento", "concluido"}


class CreateActionPlanRequest(BaseModel):
    store_id: str
    title: str
    description: str | None = None
    status: Literal["a_fazer", "em_andamento", "concluido"] = "a_fazer"
    due_date: str | None = None
    responsible_ids: list[str] | None = None


class UpdateActionPlanRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: Literal["a_fazer", "em_andamento", "concluido"] | None = None
    due_date: str | None = None
    responsible_ids: list[str] | None = None


class CreateStepRequest(BaseModel):
    title: str
    description: str | None = None
    due_date: str | None = None
    sort_order: int = 0


class UpdateStepRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: str | None = None
    done: bool | None = None
    sort_order: int | None = None


class UpdateStatusRequest(BaseModel):
    status: Literal["a_fazer", "em_andamento", "concluido"]
