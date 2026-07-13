from pydantic import BaseModel


class CreateServiceRequest(BaseModel):
    key: str
    name: str
    type: str
    what_it_is: str | None = None
    what_it_does: str | None = None
    upsell_pitch: str | None = None
    feature_keys: list[str] = []
    sort_order: int = 0


class CreatePlanRequest(BaseModel):
    key: str
    name: str
    service_keys: list[str] = []
    max_stores: int | None = None
    price_month: float | None = None


class CreateCompanyRequest(BaseModel):
    name: str
    cnpj: str | None = None
    responsible_name: str | None = None


class CreateSubscriptionRequest(BaseModel):
    company_id: str
    plan_id: str
    status: str
    trial_ends_at: str | None = None
    notes: str | None = None


class ToggleStoreServiceRequest(BaseModel):
    service_key: str
    enabled: bool


class RegisterInterestRequest(BaseModel):
    store_id: str
    service_key: str
