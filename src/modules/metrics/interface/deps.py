from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.modules.metrics.application.dashboard import DashboardUseCase
from src.modules.metrics.application.marketing import MarketingUseCase
from src.modules.metrics.application.projections import ProjectionsUseCase
from src.modules.metrics.application.reports import ReportUseCase
from src.modules.metrics.domain.working_days import WorkingDays
from src.modules.metrics.infrastructure.qualification_reader import QualificationReader
from src.modules.metrics.infrastructure.reader import MetricsLeadReader
from src.modules.stores.application.get_accessible_stores import GetAccessibleStoreIdsUseCase
from src.modules.stores.infrastructure.repository import SqlAlchemyStoreAccessReader, SqlAlchemyStoreRepository
from src.shared.infrastructure.database import get_session


def get_dashboard_uc(session: AsyncSession = Depends(get_session)) -> DashboardUseCase:
    return DashboardUseCase(MetricsLeadReader(session), QualificationReader(session))


def get_report_uc(session: AsyncSession = Depends(get_session)) -> ReportUseCase:
    return ReportUseCase(MetricsLeadReader(session), QualificationReader(session))


def get_marketing_uc(session: AsyncSession = Depends(get_session)) -> MarketingUseCase:
    return MarketingUseCase(MetricsLeadReader(session), QualificationReader(session))


def get_projections_uc(session: AsyncSession = Depends(get_session)) -> ProjectionsUseCase:
    return ProjectionsUseCase(MetricsLeadReader(session), WorkingDays())


def get_accessible_uc(session: AsyncSession = Depends(get_session)) -> GetAccessibleStoreIdsUseCase:
    return GetAccessibleStoreIdsUseCase(SqlAlchemyStoreAccessReader(session))


def get_user_repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session)


def get_store_repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemyStoreRepository:
    return SqlAlchemyStoreRepository(session)


def get_indicators_report_uc(session: AsyncSession = Depends(get_session)) -> object:
    from src.modules.metrics.application.indicators_report import IndicatorsReportUseCase
    from src.modules.indicators.infrastructure.repository import IndicatorRepository
    from src.modules.goals.infrastructure.repository import GoalRepository
    return IndicatorsReportUseCase(IndicatorRepository(session), GoalRepository(session))
