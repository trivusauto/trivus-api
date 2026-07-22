from fastapi import APIRouter, Depends, Query

from src.modules.crm.application.funnels import CreateStageUseCase, ListFunnelsUseCase, RenameStageUseCase
from src.modules.crm.application.leads import (
    CreateLeadUseCase,
    DeleteLeadUseCase,
    ListLeadsUseCase,
    UpdateLeadUseCase,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.crm.application.move_lead import MoveLeadStageUseCase
from src.modules.crm.infrastructure.store_flags import StoreFlagsReader
from src.modules.crm.application.patches import SetAgendamentoUseCase, SetCompareceuUseCase, SetFechamentoUseCase
from src.modules.crm.application.sync_template import SyncTemplateToClientsUseCase
from src.modules.crm.application.templates_crud import CreateTemplateUseCase, ListTemplatesUseCase
from src.modules.crm.domain.lead_patch import LeadPatch
from src.modules.crm.domain.stage_rules import StageRules
from src.modules.crm.infrastructure.repositories import (
    ActivityRepository,
    CoolingRepository,
    HistoryRepository,
    LeadRepository,
    StageRepository,
)
from src.modules.crm.interface.deps import (
    get_activity_repo,
    get_cooling_repo,
    get_create_stage_uc,
    get_create_template_uc,
    get_history_repo,
    get_lead_repo,
    get_list_funnels_uc,
    get_list_templates_uc,
    get_rename_stage_uc,
    get_stage_repo,
    get_sync_template_uc,
)
from src.modules.crm.interface.schemas import (
    AgendamentoRequest,
    CompareceuRequest,
    CoolingRuleIn,
    CreateLeadRequest,
    CreateStageRequest,
    CreateTemplateRequest,
    FechamentoRequest,
    MoveLeadRequest,
    RenameRequest,
    UpdateLeadRequest,
)
from src.modules.auth.infrastructure.repository import SqlAlchemyUserRepository
from src.shared.infrastructure.database import get_session
from src.shared.interface.feature_gate import require_feature
from src.shared.interface.store_access import assert_store_access, require_store_access
from src.shared.interface.auth_deps import CurrentUser, get_current_user
from src.shared.interface.rbac import require_roles

router = APIRouter(prefix="/crm", tags=["crm"])
admin_router = APIRouter(tags=["crm-admin"])  # sem prefixo: rotas /admin/crm/*


@router.get("/funnels", dependencies=[Depends(require_feature("crm.kanban")), Depends(require_store_access)])
async def list_funnels(
    store_id: str = Query(...),
    _: CurrentUser = Depends(get_current_user),
    uc: ListFunnelsUseCase = Depends(get_list_funnels_uc),
) -> list[dict[str, object]]:
    return await uc.execute(store_id)


@router.post("/stages", status_code=201)
async def create_stage(
    body: CreateStageRequest,
    _: CurrentUser = Depends(get_current_user),
    uc: CreateStageUseCase = Depends(get_create_stage_uc),
) -> dict[str, object]:
    return await uc.execute(body.funnel_id, body.name, body.sort_order)


@router.patch("/stages/{stage_id}")
async def rename_stage(
    stage_id: str,
    body: RenameRequest,
    _: CurrentUser = Depends(get_current_user),
    uc: RenameStageUseCase = Depends(get_rename_stage_uc),
) -> dict[str, object]:
    return await uc.execute(stage_id, body.name)


@router.get("/leads", dependencies=[Depends(require_feature("crm.kanban")), Depends(require_store_access)])
async def list_leads(
    store_id: str = Query(...),
    assigned_to: str | None = Query(None, description="Filtra por responsável (id do usuário ou '__unassigned__')."),
    user: CurrentUser = Depends(get_current_user),
    repo: LeadRepository = Depends(get_lead_repo),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    return await ListLeadsUseCase(repo, SqlAlchemyUserRepository(session)).execute(store_id, user, assigned_to)


@router.post("/leads", status_code=201)
async def create_lead(
    body: CreateLeadRequest,
    user: CurrentUser = Depends(get_current_user),
    repo: LeadRepository = Depends(get_lead_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    await assert_store_access(body.store_id, user, session)
    return await CreateLeadUseCase(repo).execute(body.model_dump(exclude_none=True))


@router.patch("/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    body: UpdateLeadRequest,
    _: CurrentUser = Depends(get_current_user),
    repo: LeadRepository = Depends(get_lead_repo),
) -> dict[str, object]:
    return await UpdateLeadUseCase(repo).execute(lead_id, body.model_dump(exclude_none=True))


@router.delete("/leads/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: str,
    _: CurrentUser = Depends(get_current_user),
    repo: LeadRepository = Depends(get_lead_repo),
) -> None:
    await DeleteLeadUseCase(repo).execute(lead_id)


@router.patch("/leads/{lead_id}/stage")
async def move_lead(
    lead_id: str,
    body: MoveLeadRequest,
    user: CurrentUser = Depends(get_current_user),
    leads: LeadRepository = Depends(get_lead_repo),
    stages: StageRepository = Depends(get_stage_repo),
    history: HistoryRepository = Depends(get_history_repo),
    activity: ActivityRepository = Depends(get_activity_repo),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    uc = MoveLeadStageUseCase(leads, stages, history, activity, StageRules(),
                              store_flags=StoreFlagsReader(session))
    return await uc.execute(lead_id, body.to_stage_id, user)


@router.patch("/leads/{lead_id}/agendamento")
async def set_agendamento(
    lead_id: str,
    body: AgendamentoRequest,
    user: CurrentUser = Depends(get_current_user),
    repo: LeadRepository = Depends(get_lead_repo),
) -> dict[str, object]:
    return await SetAgendamentoUseCase(repo, LeadPatch()).execute(lead_id, body.data_agendamento, body.hora_agendamento, user)


@router.patch("/leads/{lead_id}/comparecimento")
async def set_comparecimento(
    lead_id: str,
    body: CompareceuRequest,
    _: CurrentUser = Depends(get_current_user),
    repo: LeadRepository = Depends(get_lead_repo),
) -> dict[str, object]:
    return await SetCompareceuUseCase(repo, LeadPatch()).execute(lead_id, body.compareceu)


@router.patch("/leads/{lead_id}/fechamento")
async def set_fechamento(
    lead_id: str,
    body: FechamentoRequest,
    _: CurrentUser = Depends(get_current_user),
    repo: LeadRepository = Depends(get_lead_repo),
) -> dict[str, object]:
    return await SetFechamentoUseCase(repo, LeadPatch()).execute(lead_id, body.receita, body.despesa, body.rentabilidade)


@router.put("/stages/{stage_id}/cooling-rules")
async def set_cooling_rules(
    stage_id: str,
    body: list[CoolingRuleIn],
    _: CurrentUser = Depends(get_current_user),
    repo: CoolingRepository = Depends(get_cooling_repo),
) -> list[dict[str, object]]:
    rules: list[dict[str, object]] = [r.model_dump() for r in body]
    return await repo.save(stage_id, rules)


@admin_router.get("/admin/crm/templates")
async def list_templates(
    _: CurrentUser = Depends(require_roles("admin")),
    uc: ListTemplatesUseCase = Depends(get_list_templates_uc),
) -> list[dict[str, object]]:
    return await uc.execute()


@admin_router.post("/admin/crm/templates", status_code=201)
async def create_template(
    body: CreateTemplateRequest,
    _: CurrentUser = Depends(require_roles("admin")),
    uc: CreateTemplateUseCase = Depends(get_create_template_uc),
) -> dict[str, object]:
    return await uc.execute(body.name, body.stages)


@admin_router.post("/admin/crm/templates/{template_id}/sync", status_code=200)
async def sync_template(
    template_id: str,
    _: CurrentUser = Depends(require_roles("admin")),
    uc: SyncTemplateToClientsUseCase = Depends(get_sync_template_uc),
) -> dict[str, object]:
    await uc.execute(template_id)
    return {"ok": True}
