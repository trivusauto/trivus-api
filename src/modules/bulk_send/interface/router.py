from fastapi import APIRouter, Body, Depends

from src.modules.bulk_send.application.create import CreateBulkSendUseCase
from src.modules.bulk_send.infrastructure.repository import BulkSendContactRepository, BulkSendRepository
from src.modules.bulk_send.interface.deps import (
    get_contacts_repo, get_create_uc, get_sends_repo, require_n8n_token,
)
from src.shared.interface.auth_deps import CurrentUser
from src.shared.interface.rbac import require_roles

router = APIRouter(tags=["bulk-send"])


@router.get("/admin/bulk-sends")
async def list_sends(_: CurrentUser = Depends(require_roles("admin")),
                     repo: BulkSendRepository = Depends(get_sends_repo)) -> list[dict[str, object]]:
    return await repo.list()


@router.post("/admin/bulk-sends", status_code=201)
async def create_send(body: dict[str, object] = Body(...), _: CurrentUser = Depends(require_roles("admin")),
                      uc: CreateBulkSendUseCase = Depends(get_create_uc)) -> dict[str, object]:
    return await uc.execute(body)


@router.get("/admin/bulk-sends/{send_id}/logs")
async def logs(send_id: str, _: CurrentUser = Depends(require_roles("admin")),
               repo: BulkSendContactRepository = Depends(get_contacts_repo)) -> list[dict[str, object]]:
    return await repo.list_ordered(send_id)


@router.patch("/integrations/bulk-send/contacts/{contact_id}/status",
              dependencies=[Depends(require_n8n_token)])
async def update_contact_status(contact_id: str, body: dict[str, object] = Body(...),
                                repo: BulkSendContactRepository = Depends(get_contacts_repo)) -> dict[str, object]:
    error_message = body.get("error_message")
    await repo.update_status(contact_id, str(body["status"]),
                             str(error_message) if error_message is not None else None)
    return {"ok": True}
