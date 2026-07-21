from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.integrations.meta.application.sync import SyncMetaSpendUseCase
from src.modules.integrations.meta.domain.client import MetaAdsClient
from src.modules.integrations.meta.infrastructure.http_client import HttpMetaClient
from src.modules.integrations.meta.infrastructure.mock_client import MockMetaClient
from src.modules.integrations.meta.infrastructure.reader import MetaCampaignReader
from src.modules.integrations.meta.infrastructure.repository import CampaignDailySpendRepository
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.settings import get_settings


def build_meta_client() -> MetaAdsClient:
    """HTTP real quando META_ENABLED=true; caso contrário, mock determinístico."""
    settings = get_settings()
    if settings.meta_enabled:
        return HttpMetaClient(settings.meta_access_token)
    return MockMetaClient()


def get_sync_uc(session: AsyncSession = Depends(get_session)) -> SyncMetaSpendUseCase:
    return SyncMetaSpendUseCase(MetaCampaignReader(session),
                                CampaignDailySpendRepository(session), build_meta_client())


def require_meta_token(x_meta_token: str | None = Header(default=None)) -> None:
    """Mesmo padrão do n8n/billing: 401 se o header x-meta-token não bater (ou faltar)."""
    if x_meta_token != get_settings().meta_token:
        raise HTTPException(status_code=401, detail="token inválido")
