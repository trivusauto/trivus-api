from pydantic import BaseModel, field_validator


class UpsertIndicatorRequest(BaseModel):
    store_id: str
    reference_date: str
    origin: str
    origin_custom: str | None = None
    total_leads: int = 0
    qualified_leads: int = 0
    scheduled_leads: int = 0
    attended_leads: int = 0
    converted_leads: int = 0
    profitability: float | None = None
    daily_expenses: float | None = None
    notes: str | None = None

    @field_validator("total_leads", "qualified_leads", "scheduled_leads", "attended_leads", "converted_leads")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("must be >= 0")
        return v
