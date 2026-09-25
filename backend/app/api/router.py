from fastapi import APIRouter

from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.clinics import router as clinics_router
from app.api.routes.health import router as health_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(audit_router, prefix="/audit-events", tags=["audit"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(clinics_router, prefix="/clinics", tags=["clinics"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
