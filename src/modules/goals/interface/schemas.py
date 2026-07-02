from pydantic import BaseModel, field_validator

_ORIGINS = {"receptivo", "prospeccao", "outros"}


class UpsertGoalRequest(BaseModel):
    store_id: str
    year: int
    month: int
    origin: str
    leads_quantity: int = 0
    qualified_quantity: int = 0
    scheduled_quantity: int = 0
    attended_quantity: int = 0
    conversions_quantity: int = 0
    profitability_goal: float | None = None
    average_ticket_goal: float | None = None

    @field_validator("month")
    @classmethod
    def valid_month(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("month must be 1-12")
        return v

    @field_validator("origin")
    @classmethod
    def valid_origin(cls, v: str) -> str:
        if v not in _ORIGINS:
            raise ValueError(f"origin must be one of {_ORIGINS}")
        return v

    @field_validator("leads_quantity", "qualified_quantity", "scheduled_quantity", "attended_quantity", "conversions_quantity")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("must be >= 0")
        return v
