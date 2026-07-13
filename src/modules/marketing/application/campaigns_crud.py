from src.modules.marketing.domain.entities import Campaign
from src.modules.marketing.infrastructure.repository import CampaignRepository


class ListCampaignsUseCase:
    def __init__(self, campaigns: CampaignRepository) -> None:
        self._campaigns = campaigns

    async def execute(self, store_id: str) -> list[Campaign]:
        return await self._campaigns.list_for_store(store_id)


class CreateCampaignUseCase:
    def __init__(self, campaigns: CampaignRepository) -> None:
        self._campaigns = campaigns

    async def execute(self, data: dict[str, object]) -> Campaign:
        return await self._campaigns.create(data)


class UpdateCampaignUseCase:
    def __init__(self, campaigns: CampaignRepository) -> None:
        self._campaigns = campaigns

    async def execute(self, campaign_id: str, data: dict[str, object]) -> Campaign:
        return await self._campaigns.update(campaign_id, data)
