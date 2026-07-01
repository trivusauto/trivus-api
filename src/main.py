from fastapi import FastAPI
from src.modules.auth.interface.router import router as auth_router
from src.modules.health.interface.router import router as health_router
from src.modules.crm.interface.router import router as crm_router
from src.modules.stores.interface.router import router as stores_router
from src.modules.users.interface.router import router as users_router
from src.modules.webhook.interface.router import router as webhook_router
from src.shared.interface.error_handlers import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Trivus Backend")
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(stores_router)
    app.include_router(crm_router)
    app.include_router(users_router)
    app.include_router(webhook_router)
    return app


app = create_app()
