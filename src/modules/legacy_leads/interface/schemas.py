from pydantic import BaseModel


class CreateLegacyLeadRequest(BaseModel):
    store_id: str
    name: str | None = None
    phone: str | None = None
    car: str | None = None
    city: str | None = None
    origin: str | None = None
    origin_custom: str | None = None
    entry_date: str | None = None


class UpdateLegacyLeadRequest(BaseModel):
    qualified: bool | None = None
    disqualified: bool | None = None
    disqualification_reason: str | None = None
    scheduled: bool | None = None
    attended: bool | None = None
    converted: bool | None = None
    profitability: float | None = None
