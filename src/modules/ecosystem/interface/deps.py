from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.ecosystem.application.billing_events import HandleBillingEventUseCase
from src.modules.ecosystem.application.catalog import GetCatalogUseCase, RegisterInterestUseCase
from src.modules.ecosystem.application.companies import (
    CreateCompanyUseCase, ListCompaniesUseCase, UpdateCompanyUseCase,
)
from src.modules.ecosystem.application.plans_crud import CreatePlanUseCase, UpdatePlanUseCase
from src.modules.ecosystem.application.services_crud import (
    CreateServiceUseCase, DeactivateServiceUseCase, UpdateServiceUseCase,
)
from src.modules.ecosystem.application.store_services import ToggleStoreServiceUseCase
from src.modules.ecosystem.application.subscriptions import (
    ChangeSubscriptionPlanUseCase, ChangeSubscriptionStatusUseCase, CreateSubscriptionUseCase,
)
from src.modules.ecosystem.infrastructure.company_stores import CompanyStoresReader
from src.modules.ecosystem.infrastructure.entitlement_service import EntitlementService
from src.modules.ecosystem.infrastructure.interest_notifier import InterestNotifier
from src.modules.ecosystem.infrastructure.repositories import (
    CompanyRepository, PlanRepository, ServiceInterestRepository, ServiceRepository,
    StoreServiceRepository, SubscriptionPaymentRepository, SubscriptionRepository,
)
from src.shared.infrastructure.database import get_session
from src.shared.infrastructure.settings import get_settings


def get_create_service_uc(s: AsyncSession = Depends(get_session)) -> CreateServiceUseCase:
    return CreateServiceUseCase(ServiceRepository(s))


def get_update_service_uc(s: AsyncSession = Depends(get_session)) -> UpdateServiceUseCase:
    return UpdateServiceUseCase(ServiceRepository(s))


def get_deactivate_service_uc(s: AsyncSession = Depends(get_session)) -> DeactivateServiceUseCase:
    return DeactivateServiceUseCase(ServiceRepository(s), PlanRepository(s))


def get_services_repo(s: AsyncSession = Depends(get_session)) -> ServiceRepository:
    return ServiceRepository(s)


def get_create_plan_uc(s: AsyncSession = Depends(get_session)) -> CreatePlanUseCase:
    return CreatePlanUseCase(PlanRepository(s), ServiceRepository(s))


def get_update_plan_uc(s: AsyncSession = Depends(get_session)) -> UpdatePlanUseCase:
    return UpdatePlanUseCase(PlanRepository(s), ServiceRepository(s))


def get_plans_repo(s: AsyncSession = Depends(get_session)) -> PlanRepository:
    return PlanRepository(s)


def get_list_companies_uc(s: AsyncSession = Depends(get_session)) -> ListCompaniesUseCase:
    return ListCompaniesUseCase(CompanyRepository(s))


def get_create_company_uc(s: AsyncSession = Depends(get_session)) -> CreateCompanyUseCase:
    return CreateCompanyUseCase(CompanyRepository(s))


def get_update_company_uc(s: AsyncSession = Depends(get_session)) -> UpdateCompanyUseCase:
    return UpdateCompanyUseCase(CompanyRepository(s))


def get_create_subscription_uc(s: AsyncSession = Depends(get_session)) -> CreateSubscriptionUseCase:
    return CreateSubscriptionUseCase(SubscriptionRepository(s), PlanRepository(s), CompanyStoresReader(s))


def get_change_sub_status_uc(s: AsyncSession = Depends(get_session)) -> ChangeSubscriptionStatusUseCase:
    return ChangeSubscriptionStatusUseCase(SubscriptionRepository(s))


def get_change_sub_plan_uc(s: AsyncSession = Depends(get_session)) -> ChangeSubscriptionPlanUseCase:
    return ChangeSubscriptionPlanUseCase(SubscriptionRepository(s), PlanRepository(s))


def get_subs_repo(s: AsyncSession = Depends(get_session)) -> SubscriptionRepository:
    return SubscriptionRepository(s)


def get_toggle_store_service_uc(s: AsyncSession = Depends(get_session)) -> ToggleStoreServiceUseCase:
    return ToggleStoreServiceUseCase(StoreServiceRepository(s), SubscriptionRepository(s),
                                     PlanRepository(s), CompanyStoresReader(s))


def get_catalog_uc(s: AsyncSession = Depends(get_session)) -> GetCatalogUseCase:
    return GetCatalogUseCase(ServiceRepository(s), EntitlementService(s))


def get_register_interest_uc(s: AsyncSession = Depends(get_session)) -> RegisterInterestUseCase:
    return RegisterInterestUseCase(ServiceInterestRepository(s), CompanyStoresReader(s),
                                   InterestNotifier(get_settings().n8n_interest_webhook_url))


def get_interests_repo(s: AsyncSession = Depends(get_session)) -> ServiceInterestRepository:
    return ServiceInterestRepository(s)


def get_entitlements(s: AsyncSession = Depends(get_session)) -> EntitlementService:
    return EntitlementService(s)


def require_billing_integration(x_billing_token: str = Header(...)) -> None:
    settings = get_settings()
    if not settings.billing_gateway_enabled:
        raise HTTPException(status_code=409,
                            detail="Integração de cobrança desativada (BILLING_GATEWAY_ENABLED=false).")
    if x_billing_token != settings.billing_token:
        raise HTTPException(status_code=401, detail="token inválido")


def get_billing_event_uc(s: AsyncSession = Depends(get_session)) -> HandleBillingEventUseCase:
    return HandleBillingEventUseCase(SubscriptionRepository(s), SubscriptionPaymentRepository(s))
