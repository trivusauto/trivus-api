from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.marketing.application.campaigns_crud import (
    CreateCampaignUseCase, ListCampaignsUseCase, UpdateCampaignUseCase,
)
from src.modules.marketing.infrastructure.repository import CampaignRepository
from src.shared.infrastructure.database import get_session


def _campaigns(session: AsyncSession = Depends(get_session)) -> CampaignRepository:
    return CampaignRepository(session)


def get_list_campaigns_uc(repo: CampaignRepository = Depends(_campaigns)) -> ListCampaignsUseCase:
    return ListCampaignsUseCase(repo)


def get_create_campaign_uc(repo: CampaignRepository = Depends(_campaigns)) -> CreateCampaignUseCase:
    return CreateCampaignUseCase(repo)


def get_update_campaign_uc(repo: CampaignRepository = Depends(_campaigns)) -> UpdateCampaignUseCase:
    return UpdateCampaignUseCase(repo)
