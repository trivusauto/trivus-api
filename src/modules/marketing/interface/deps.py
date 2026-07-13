from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.marketing.application.campaigns_crud import (
    CreateCampaignUseCase, ListCampaignsUseCase, UpdateCampaignUseCase,
)
from src.modules.marketing.application.campaigns_funnels import CampaignsFunnelsUseCase  # noqa: TC001
from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase  # noqa: TC001
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


def get_marketing_funnel_uc(session: AsyncSession = Depends(get_session)) -> "MarketingFunnelUseCase":
    from src.modules.goals.infrastructure.repository import GoalRepository
    from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase
    from src.modules.metrics.infrastructure.investment_reader import InvestmentReader
    from src.modules.metrics.infrastructure.reader import MetricsLeadReader
    from src.modules.metrics.infrastructure.stage_reach_reader import StageReachReader
    return MarketingFunnelUseCase(MetricsLeadReader(session), StageReachReader(session),
                                  InvestmentReader(session), CampaignRepository(session),
                                  GoalRepository(session))


def get_campaigns_funnels_uc(session: AsyncSession = Depends(get_session)) -> "CampaignsFunnelsUseCase":
    from src.modules.marketing.application.campaigns_funnels import CampaignsFunnelsUseCase
    return CampaignsFunnelsUseCase(get_marketing_funnel_uc(session), CampaignRepository(session))
