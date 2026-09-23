from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
        description="DentalApp demo API — gerçek hasta verisi girmeyiniz.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.get("/", tags=["system"])
    def root() -> dict[str, str | bool]:
        return {
            "name": settings.app_name,
            "status": "ok",
            "demo_mode": settings.demo_mode,
            "warning": "DEMO — Gerçek hasta verisi girmeyiniz.",
        }

    return application


app = create_app()
