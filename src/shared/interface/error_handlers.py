from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.shared.domain.errors import DomainError, ForbiddenError, NotFoundError, UnauthorizedError

_STATUS: dict[type[DomainError], int] = {UnauthorizedError: 401, ForbiddenError: 403, NotFoundError: 404}


def register_error_handlers(app: FastAPI) -> None:
    async def handler(request: Request, exc: Exception) -> JSONResponse:
        status = _STATUS.get(type(exc), 400)  # type: ignore[arg-type]
        return JSONResponse(status_code=status, content={"error": str(exc)})

    for exc_type in (UnauthorizedError, ForbiddenError, NotFoundError):
        app.add_exception_handler(exc_type, handler)
