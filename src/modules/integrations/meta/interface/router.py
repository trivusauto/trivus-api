from fastapi import APIRouter, Depends

from src.modules.integrations.meta.application.sync import SyncMetaSpendUseCase
from src.modules.integrations.meta.interface.deps import get_sync_uc, require_meta_token
from src.modules.integrations.meta.interface.schemas import MetaSyncRequest

router = APIRouter(tags=["integrations-meta"])


@router.post("/integrations/meta/sync", dependencies=[Depends(require_meta_token)])
async def sync_meta_spend(body: MetaSyncRequest | None = None,
                          uc: SyncMetaSpendUseCase = Depends(get_sync_uc)) -> dict[str, object]:
    payload = body or MetaSyncRequest()
    return await uc.execute(payload.store_id, payload.since, payload.until)
