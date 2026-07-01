from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.infrastructure.repositories import FunnelRepository, HistoryRepository, LeadRepository, StageRepository
from src.modules.webhook.application.handle_zapi import HandleZapiWebhookUseCase
from src.modules.webhook.domain.phone import Phone
from src.modules.webhook.domain.round_robin import RoundRobin
from src.modules.webhook.infrastructure.repositories import WebhookLeadRepository, WebhookStoreRepository, WebhookUserRepository
from src.shared.infrastructure.database import get_session


def get_handle_zapi_uc(session: AsyncSession = Depends(get_session)) -> HandleZapiWebhookUseCase:
    return HandleZapiWebhookUseCase(
        WebhookStoreRepository(session),
        WebhookLeadRepository(session),
        FunnelRepository(session),
        StageRepository(session),
        LeadRepository(session),
        WebhookUserRepository(session),
        HistoryRepository(session),
        Phone(),
        RoundRobin(),
    )
