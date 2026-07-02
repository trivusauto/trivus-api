from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.legacy_leads.application.use_cases import (
    CreateLegacyLeadUseCase, DeleteLegacyLeadUseCase, ListLegacyLeadsUseCase, UpdateLegacyLeadUseCase,
)
from src.modules.legacy_leads.infrastructure.repository import LegacyLeadRepository
from src.shared.infrastructure.database import get_session


def _repo(session: AsyncSession = Depends(get_session)) -> LegacyLeadRepository:
    return LegacyLeadRepository(session)


def list_uc(r: LegacyLeadRepository = Depends(_repo)) -> ListLegacyLeadsUseCase:
    return ListLegacyLeadsUseCase(r)


def create_uc(r: LegacyLeadRepository = Depends(_repo)) -> CreateLegacyLeadUseCase:
    return CreateLegacyLeadUseCase(r)


def update_uc(r: LegacyLeadRepository = Depends(_repo)) -> UpdateLegacyLeadUseCase:
    return UpdateLegacyLeadUseCase(r)


def delete_uc(r: LegacyLeadRepository = Depends(_repo)) -> DeleteLegacyLeadUseCase:
    return DeleteLegacyLeadUseCase(r)
