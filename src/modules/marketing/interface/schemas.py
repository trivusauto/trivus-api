from pydantic import BaseModel


class CreateCampaignRequest(BaseModel):
    store_id: str
    name: str
    started_at: str            # YYYY-MM-DD
    ended_at: str | None = None
    budget: float | None = None
    link_code: str | None = None


class UpdateCampaignRequest(BaseModel):
    name: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    budget: float | None = None
    link_code: str | None = None
    meta_campaign_id: str | None = None


class CampaignResponse(BaseModel):
    id: str
    store_id: str
    name: str
    started_at: str
    ended_at: str | None
    budget: float | None
    link_code: str | None
    meta_campaign_id: str | None = None
