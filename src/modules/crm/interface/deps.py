from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

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


def get_list_funnels_uc(session: AsyncSession = Depends(get_session)) -> ListFunnelsUseCase:
    return ListFunnelsUseCase(FunnelRepository(session), StageRepository(session))


def get_create_stage_uc(session: AsyncSession = Depends(get_session)) -> CreateStageUseCase:
    return CreateStageUseCase(StageRepository(session))


def get_rename_stage_uc(session: AsyncSession = Depends(get_session)) -> RenameStageUseCase:
    return RenameStageUseCase(StageRepository(session))


def get_lead_repo(session: AsyncSession = Depends(get_session)) -> LeadRepository:
    return LeadRepository(session)


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
