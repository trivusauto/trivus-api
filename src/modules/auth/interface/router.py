from fastapi import APIRouter, Depends
from src.modules.auth.application.dto import LoginCommand
from src.modules.auth.application.login import LoginUseCase
from src.modules.auth.interface.deps import get_login_use_case
from src.modules.auth.interface.schemas import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, uc: LoginUseCase = Depends(get_login_use_case)) -> LoginResponse:
    result = await uc.execute(LoginCommand(email=body.email, password=body.password))
    u = result.user
    return LoginResponse(
        access_token=result.access_token,
        user=UserResponse(id=u.id, email=u.email, name=u.name, role=u.role, parent_store_id=u.parent_store_id),
    )
