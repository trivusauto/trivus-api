from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.metrics.application.dashboard import DashboardUseCase
from src.modules.metrics.application.projections import ProjectionsUseCase
from src.modules.metrics.application.reports import ReportUseCase
from src.modules.metrics.domain.working_days import WorkingDays
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreAccessReader
from src.shared.infrastructure.database import get_session


def get_dashboard_uc(session: AsyncSession = Depends(get_session)) -> DashboardUseCase:
    return DashboardUseCase(MetricsLeadReader(session))


def get_report_uc(session: AsyncSession = Depends(get_session)) -> ReportUseCase:
    return ReportUseCase(MetricsLeadReader(session))


def get_projections_uc(session: AsyncSession = Depends(get_session)) -> ProjectionsUseCase:
    return ProjectionsUseCase(MetricsLeadReader(session), WorkingDays())


def get_accessible_uc(session: AsyncSession = Depends(get_session)) -> GetAccessibleStoreIdsUseCase:
    return GetAccessibleStoreIdsUseCase(SqlAlchemyStoreAccessReader(session))


def get_user_repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)
