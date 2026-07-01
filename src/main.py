from fastapi import FastAPI
from src.modules.health.interface.router import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Trivus Backend")
    app.include_router(health_router)
    return app


app = create_app()
