from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.patient_data import get_patient_data_cipher


def create_app() -> FastAPI:
    settings = get_settings()
    get_patient_data_cipher()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
        description="DentFlow demo API — gerçek hasta verisi girmeyiniz.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "Upload-Offset", "X-CSRF-Token"],
        expose_headers=["Upload-Offset"],
    )
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if (
            request.url.path.startswith(settings.api_prefix)
            and "cache-control" not in response.headers
        ):
            response.headers["Cache-Control"] = "no-store"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

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
