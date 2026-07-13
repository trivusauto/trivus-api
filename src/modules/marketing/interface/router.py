from fastapi import APIRouter, Depends, Query

from src.modules.marketing.application.campaigns_crud import (
    CreateCampaignUseCase, ListCampaignsUseCase, UpdateCampaignUseCase,
)
from src.modules.marketing.domain.entities import Campaign
from src.modules.marketing.application.campaigns_funnels import CampaignsFunnelsUseCase
from src.modules.marketing.application.marketing_funnel import MarketingFunnelUseCase
from src.modules.marketing.interface.deps import (
    get_campaigns_funnels_uc, get_create_campaign_uc, get_list_campaigns_uc,
    get_marketing_funnel_uc, get_update_campaign_uc,
)
from src.modules.metrics.interface.deps import get_accessible_uc
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.shared.domain.errors import ForbiddenError
from src.modules.marketing.interface.schemas import (
    CampaignResponse, CreateCampaignRequest, UpdateCampaignRequest,
)
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(tags=["marketing"])


def _resp(c: Campaign) -> CampaignResponse:
    return CampaignResponse(id=c.id, store_id=c.store_id, name=c.name, started_at=c.started_at,
                            ended_at=c.ended_at, budget=c.budget, link_code=c.link_code)


@router.get("/campaigns")
async def list_campaigns(store_id: str = Query(...), _: CurrentUser = Depends(get_current_user),
                         uc: ListCampaignsUseCase = Depends(get_list_campaigns_uc)) -> list[CampaignResponse]:
    return [_resp(c) for c in await uc.execute(store_id)]


@router.post("/campaigns", status_code=201)
async def create_campaign(body: CreateCampaignRequest, _: CurrentUser = Depends(get_current_user),
                          uc: CreateCampaignUseCase = Depends(get_create_campaign_uc)) -> CampaignResponse:
    return _resp(await uc.execute(body.model_dump()))


@router.patch("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, body: UpdateCampaignRequest,
                          _: CurrentUser = Depends(get_current_user),
                          uc: UpdateCampaignUseCase = Depends(get_update_campaign_uc)) -> CampaignResponse:
    return _resp(await uc.execute(campaign_id, body.model_dump(exclude_unset=True)))


async def _check_scope(user: CurrentUser, store_id: str,
                       access: GetAccessibleStoreIdsUseCase) -> None:
    scope = await access.execute(user)
    if scope is not None and store_id not in scope:
        raise ForbiddenError("Loja fora do escopo.")


@router.get("/marketing/funnel")
async def marketing_funnel(store_id: str = Query(...), start: str = Query(...), end: str = Query(...),
                           campaign_id: str | None = Query(None),
                           user: CurrentUser = Depends(get_current_user),
                           uc: MarketingFunnelUseCase = Depends(get_marketing_funnel_uc),
                           access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc)) -> dict[str, object]:
    await _check_scope(user, store_id, access)
    return await uc.execute([store_id], start, end, campaign_id)


@router.get("/marketing/by-campaign")
async def marketing_by_campaign(store_id: str = Query(...), start: str = Query(...), end: str = Query(...),
                                user: CurrentUser = Depends(get_current_user),
                                uc: CampaignsFunnelsUseCase = Depends(get_campaigns_funnels_uc),
                                access: GetAccessibleStoreIdsUseCase = Depends(get_accessible_uc)) -> list[dict[str, object]]:
    await _check_scope(user, store_id, access)
    return await uc.execute(store_id, start, end)
