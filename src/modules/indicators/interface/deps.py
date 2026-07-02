from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.indicators.application.use_cases import ListIndicatorsUseCase, UpsertIndicatorUseCase
from src.modules.indicators.infrastructure.repository import IndicatorRepository
from src.shared.infrastructure.database import get_session


def _repo(session: AsyncSession = Depends(get_session)) -> IndicatorRepository:
    return IndicatorRepository(session)


def list_uc(r: IndicatorRepository = Depends(_repo)) -> ListIndicatorsUseCase:
    return ListIndicatorsUseCase(r)


def upsert_uc(r: IndicatorRepository = Depends(_repo)) -> UpsertIndicatorUseCase:
    return UpsertIndicatorUseCase(r)
