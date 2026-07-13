from fastapi import APIRouter, Body, Depends, Query

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
from src.modules.ecosystem.domain.feature_keys import list_feature_keys
from src.modules.ecosystem.infrastructure.entitlement_service import EntitlementService
from src.modules.ecosystem.infrastructure.repositories import (
    PlanRepository, ServiceInterestRepository, ServiceRepository, SubscriptionRepository,
)
from src.modules.ecosystem.interface.deps import (
    get_billing_event_uc, get_catalog_uc, get_change_sub_plan_uc, get_change_sub_status_uc,
    get_create_company_uc, get_create_plan_uc, get_create_service_uc, get_create_subscription_uc,
    get_deactivate_service_uc, get_entitlements, get_interests_repo, get_list_companies_uc,
    get_plans_repo, get_register_interest_uc, get_services_repo, get_subs_repo,
    get_toggle_store_service_uc, get_update_company_uc, get_update_plan_uc, get_update_service_uc,
    require_billing_integration,
)
from src.modules.ecosystem.interface.schemas import (
    CreateCompanyRequest, CreatePlanRequest, CreateServiceRequest, CreateSubscriptionRequest,
    RegisterInterestRequest, ToggleStoreServiceRequest,
)
from src.shared.interface.auth_deps import CurrentUser, get_current_user
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["ecosystem"])

# ---------- autenticado (loja) ----------


@router.get("/ecosystem/services")
async def catalog(store_id: str = Query(...), _: CurrentUser = Depends(get_current_user),
                  uc: GetCatalogUseCase = Depends(get_catalog_uc)) -> dict[str, object]:
    return await uc.execute(store_id)


@router.get("/ecosystem/my-entitlements")
async def my_entitlements(store_id: str = Query(...), _: CurrentUser = Depends(get_current_user),
                          ent: EntitlementService = Depends(get_entitlements)) -> dict[str, object]:
    return {"feature_keys": sorted(await ent.feature_keys_for_store(store_id))}


@router.post("/ecosystem/interests", status_code=201)
async def register_interest(body: RegisterInterestRequest,
                            user: CurrentUser = Depends(get_current_user),
                            uc: RegisterInterestUseCase = Depends(get_register_interest_uc)) -> dict[str, object]:
    return await uc.execute(body.store_id, body.service_key, user.user_id)


# ---------- admin Trivus ----------


@router.get("/ecosystem/feature-keys")
async def feature_keys(_: CurrentUser = Depends(require_roles("admin"))) -> list[dict[str, str]]:
    return list_feature_keys()


@router.get("/admin/services")
async def list_services(_: CurrentUser = Depends(require_roles("admin")),
                        repo: ServiceRepository = Depends(get_services_repo)) -> list[dict[str, object]]:
    return await repo.list_all()


@router.post("/admin/services", status_code=201)
async def create_service(body: CreateServiceRequest, _: CurrentUser = Depends(require_roles("admin")),
                         uc: CreateServiceUseCase = Depends(get_create_service_uc)) -> dict[str, object]:
    return await uc.execute(body.model_dump())


@router.patch("/admin/services/{service_id}")
async def update_service(service_id: str, body: dict[str, object] = Body(...),
                         _: CurrentUser = Depends(require_roles("admin")),
                         uc: UpdateServiceUseCase = Depends(get_update_service_uc)) -> dict[str, object]:
    return await uc.execute(service_id, body)


@router.delete("/admin/services/{service_id}")
async def deactivate_service(service_id: str, _: CurrentUser = Depends(require_roles("admin")),
                             uc: DeactivateServiceUseCase = Depends(get_deactivate_service_uc)) -> dict[str, object]:
    return await uc.execute(service_id)


@router.get("/admin/plans")
async def list_plans(_: CurrentUser = Depends(require_roles("admin")),
                     repo: PlanRepository = Depends(get_plans_repo)) -> list[dict[str, object]]:
    return await repo.list_all()


@router.post("/admin/plans", status_code=201)
async def create_plan(body: CreatePlanRequest, _: CurrentUser = Depends(require_roles("admin")),
                      uc: CreatePlanUseCase = Depends(get_create_plan_uc)) -> dict[str, object]:
    return await uc.execute(body.model_dump())


@router.patch("/admin/plans/{plan_id}")
async def update_plan(plan_id: str, body: dict[str, object] = Body(...),
                      _: CurrentUser = Depends(require_roles("admin")),
                      uc: UpdatePlanUseCase = Depends(get_update_plan_uc)) -> dict[str, object]:
    return await uc.execute(plan_id, body)


@router.get("/admin/companies")
async def list_companies(_: CurrentUser = Depends(require_roles("admin")),
                         uc: ListCompaniesUseCase = Depends(get_list_companies_uc)) -> list[dict[str, object]]:
    return await uc.execute()


@router.post("/admin/companies", status_code=201)
async def create_company(body: CreateCompanyRequest, _: CurrentUser = Depends(require_roles("admin")),
                         uc: CreateCompanyUseCase = Depends(get_create_company_uc)) -> dict[str, object]:
    return await uc.execute(body.model_dump())


@router.patch("/admin/companies/{company_id}")
async def update_company(company_id: str, body: dict[str, object] = Body(...),
                         _: CurrentUser = Depends(require_roles("admin")),
                         uc: UpdateCompanyUseCase = Depends(get_update_company_uc)) -> dict[str, object]:
    return await uc.execute(company_id, body)


@router.get("/admin/subscriptions")
async def list_subscriptions(_: CurrentUser = Depends(require_roles("admin")),
                             repo: SubscriptionRepository = Depends(get_subs_repo)) -> list[dict[str, object]]:
    return await repo.list_all()


@router.post("/admin/subscriptions", status_code=201)
async def create_subscription(body: CreateSubscriptionRequest,
                              _: CurrentUser = Depends(require_roles("admin")),
                              uc: CreateSubscriptionUseCase = Depends(get_create_subscription_uc)) -> dict[str, object]:
    return await uc.execute(body.model_dump(exclude_none=True))


@router.patch("/admin/subscriptions/{subscription_id}/status")
async def change_sub_status(subscription_id: str, body: dict[str, object] = Body(...),
                            _: CurrentUser = Depends(require_roles("admin")),
                            uc: ChangeSubscriptionStatusUseCase = Depends(get_change_sub_status_uc)) -> dict[str, object]:
    return await uc.execute(subscription_id, str(body["status"]))


@router.patch("/admin/subscriptions/{subscription_id}/plan")
async def change_sub_plan(subscription_id: str, body: dict[str, object] = Body(...),
                          _: CurrentUser = Depends(require_roles("admin")),
                          uc: ChangeSubscriptionPlanUseCase = Depends(get_change_sub_plan_uc)) -> dict[str, object]:
    return await uc.execute(subscription_id, str(body["plan_id"]))


@router.put("/admin/stores/{store_id}/services")
async def toggle_store_service(store_id: str, body: ToggleStoreServiceRequest,
                               _: CurrentUser = Depends(require_roles("admin")),
                               uc: ToggleStoreServiceUseCase = Depends(get_toggle_store_service_uc)) -> dict[str, object]:
    await uc.execute(store_id, body.service_key, body.enabled)
    return {"ok": True}


@router.get("/admin/interests")
async def list_interests(status: str | None = Query(None),
                         _: CurrentUser = Depends(require_roles("admin")),
                         repo: ServiceInterestRepository = Depends(get_interests_repo)) -> list[dict[str, object]]:
    return await repo.list_by_status(status)


@router.patch("/admin/interests/{interest_id}")
async def update_interest(interest_id: str, body: dict[str, object] = Body(...),
                          _: CurrentUser = Depends(require_roles("admin")),
                          repo: ServiceInterestRepository = Depends(get_interests_repo)) -> dict[str, object]:
    return await repo.update(interest_id, body)


# ---------- integração de cobrança (framework do dono — DESLIGADA por flag) ----------


@router.post("/integrations/billing/events", status_code=201,
             dependencies=[Depends(require_billing_integration)])
async def billing_event(body: dict[str, object] = Body(...),
                        uc: HandleBillingEventUseCase = Depends(get_billing_event_uc)) -> dict[str, object]:
    return await uc.execute(body)
