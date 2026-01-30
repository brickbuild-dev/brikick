from fastapi import FastAPI

from api.v1.router import api_router
from core.config import settings
from core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    app = FastAPI(title=settings.project_name)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}
