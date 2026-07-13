from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.bulk_send.application.create import CreateBulkSendUseCase
from src.modules.bulk_send.infrastructure.n8n_client import N8nClient
from src.modules.bulk_send.infrastructure.repository import BulkSendContactRepository, BulkSendRepository
from src.modules.webhook.domain.phone import Phone
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.settings import get_settings


def get_create_uc(session: AsyncSession = Depends(get_session)) -> CreateBulkSendUseCase:
    s = get_settings()
    return CreateBulkSendUseCase(BulkSendRepository(session), BulkSendContactRepository(session),
                                 Phone(), N8nClient(s.n8n_bulk_send_webhook_url))


def get_sends_repo(session: AsyncSession = Depends(get_session)) -> BulkSendRepository:
    return BulkSendRepository(session)


def get_contacts_repo(session: AsyncSession = Depends(get_session)) -> BulkSendContactRepository:
    return BulkSendContactRepository(session)


def require_n8n_token(x_n8n_token: str = Header(...)) -> None:
    if x_n8n_token != get_settings().n8n_token:
        raise HTTPException(status_code=401, detail="token inválido")
