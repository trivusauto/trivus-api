from fastapi import FastAPI
from src.modules.action_plans.interface.router import admin_router as action_plans_admin_router, router as action_plans_router
from src.modules.auth.interface.router import router as auth_router
from src.modules.goals.interface.router import admin_router as goals_admin_router, router as goals_router
from src.modules.health.interface.router import router as health_router
from src.modules.crm.interface.router import router as crm_router
from src.modules.indicators.interface.router import router as indicators_router
from src.modules.legacy_leads.interface.router import router as legacy_leads_router
from src.modules.stores.interface.router import router as stores_router
from src.modules.users.interface.router import router as users_router
from src.modules.agenda.interface.router import router as agenda_router
from src.modules.bulk_send.interface.router import router as bulk_send_router
from src.modules.metrics.interface.router import router as metrics_router
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
    app.include_router(agenda_router)
    app.include_router(metrics_router)
    app.include_router(legacy_leads_router)
    app.include_router(indicators_router)
    app.include_router(goals_router)
    app.include_router(goals_admin_router)
    app.include_router(action_plans_router)
    app.include_router(action_plans_admin_router)
    app.include_router(bulk_send_router)
    return app


app = create_app()
