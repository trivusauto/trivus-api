from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from src.modules.webhook.application.handle_zapi import HandleZapiWebhookUseCase
from src.modules.webhook.interface.deps import get_handle_zapi_uc

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/zapi/{token}")
async def zapi(token: str, request: Request, uc: HandleZapiWebhookUseCase = Depends(get_handle_zapi_uc)) -> JSONResponse:
    body: dict[str, object] = await request.json()
    result = await uc.execute(token, body)
    status = int(str(result.pop("status", 200)))
    return JSONResponse(status_code=status, content=result)
