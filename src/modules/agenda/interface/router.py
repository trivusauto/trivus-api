from fastapi import APIRouter, Depends, Query

from src.modules.agenda.application.list_agenda import ListAgendaUseCase
from src.modules.agenda.interface.deps import get_list_agenda_uc
from src.shared.interface.feature_gate import require_feature
from src.shared.interface.store_access import require_store_access
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("", dependencies=[Depends(require_feature("agenda")), Depends(require_store_access)])
async def list_agenda(
    store_id: str = Query(...),
    apply_to: str = Query("agendamento"),
    preset: str = Query("month"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1),
    page_size: int = Query(25),
    user: CurrentUser = Depends(get_current_user),
    uc: ListAgendaUseCase = Depends(get_list_agenda_uc),
) -> dict[str, object]:
    return await uc.execute(user, {
        "store_id": store_id, "apply_to": apply_to, "preset": preset,
        "from": from_, "to": to, "search": search, "page": page, "page_size": page_size,
    })
