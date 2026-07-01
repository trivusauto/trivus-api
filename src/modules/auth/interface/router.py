from fastapi import APIRouter, Depends
from src.modules.auth.application.change_password import ChangePasswordUseCase
from src.modules.auth.application.dto import LoginCommand
from src.modules.auth.application.get_me import GetMeUseCase
from src.modules.auth.application.login import LoginUseCase
from src.modules.auth.interface.deps import get_change_password_use_case, get_login_use_case, get_me_use_case
from src.modules.auth.interface.schemas import ChangePasswordRequest, LoginRequest, LoginResponse, UserResponse
from src.shared.interface.auth_deps import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, uc: LoginUseCase = Depends(get_login_use_case)) -> LoginResponse:
    result = await uc.execute(LoginCommand(email=body.email, password=body.password))
    u = result.user
    return LoginResponse(
        access_token=result.access_token,
        user=UserResponse(id=u.id, email=u.email, name=u.name, role=u.role, parent_store_id=u.parent_store_id),
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current: CurrentUser = Depends(get_current_user),
    uc: GetMeUseCase = Depends(get_me_use_case),
) -> UserResponse:
    u = await uc.execute(current.user_id)
    return UserResponse(id=u.id, email=u.email, name=u.name, role=u.role, parent_store_id=u.parent_store_id)


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    current: CurrentUser = Depends(get_current_user),
    uc: ChangePasswordUseCase = Depends(get_change_password_use_case),
) -> None:
    await uc.execute(current.user_id, body.current_password, body.new_password)
