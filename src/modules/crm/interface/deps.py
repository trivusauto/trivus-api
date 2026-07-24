from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.crm.application.edit_guard import assert_can_edit_lead
from src.modules.crm.application.funnels import CreateStageUseCase, ListFunnelsUseCase, RenameStageUseCase
from src.modules.crm.application.sync_template import SyncTemplateToClientsUseCase
from src.modules.crm.application.templates_crud import CreateTemplateUseCase, ListTemplatesUseCase
from src.modules.crm.infrastructure.repositories import (
    ActivityRepository,
    CoolingRepository,
    FunnelRepository,
    HistoryRepository,
    LeadRepository,
    StageRepository,
)
from src.shared.infrastructure.database import get_session
from src.shared.interface.auth_deps import CurrentUser, get_current_user


def get_list_funnels_uc(session: AsyncSession = Depends(get_session)) -> ListFunnelsUseCase:
    return ListFunnelsUseCase(FunnelRepository(session), StageRepository(session))


def get_create_stage_uc(session: AsyncSession = Depends(get_session)) -> CreateStageUseCase:
    return CreateStageUseCase(StageRepository(session))


def get_rename_stage_uc(session: AsyncSession = Depends(get_session)) -> RenameStageUseCase:
    return RenameStageUseCase(StageRepository(session))


def get_lead_repo(session: AsyncSession = Depends(get_session)) -> LeadRepository:
    return LeadRepository(session)


async def guard_lead_write(
    lead_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Dependência dos endpoints de ESCRITA de lead: 403 se o lead é de outro
    colaborador e o usuário não tem autorização (ver ``edit_guard``)."""
    lead = await LeadRepository(session).get_or_raise(lead_id)
    await assert_can_edit_lead(user, lead, SqlAlchemyUserRepository(session))


def get_stage_repo(session: AsyncSession = Depends(get_session)) -> StageRepository:
    return StageRepository(session)


def get_history_repo(session: AsyncSession = Depends(get_session)) -> HistoryRepository:
    return HistoryRepository(session)


def get_activity_repo(session: AsyncSession = Depends(get_session)) -> ActivityRepository:
    return ActivityRepository(session)


def get_cooling_repo(session: AsyncSession = Depends(get_session)) -> CoolingRepository:
    return CoolingRepository(session)


def get_list_templates_uc(session: AsyncSession = Depends(get_session)) -> ListTemplatesUseCase:
    return ListTemplatesUseCase(FunnelRepository(session), StageRepository(session))


def get_create_template_uc(session: AsyncSession = Depends(get_session)) -> CreateTemplateUseCase:
    return CreateTemplateUseCase(FunnelRepository(session), StageRepository(session))


def get_sync_template_uc(session: AsyncSession = Depends(get_session)) -> SyncTemplateToClientsUseCase:
    return SyncTemplateToClientsUseCase(FunnelRepository(session), StageRepository(session), CoolingRepository(session), LeadRepository(session))
