from fastapi import APIRouter

from app.api.routes.account import router as account_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.case_delivery import router as case_delivery_router
from app.api.routes.case_design import router as case_design_router
from app.api.routes.case_production import router as case_production_router
from app.api.routes.case_returns import router as case_returns_router
from app.api.routes.case_transfers import router as case_transfers_router
from app.api.routes.case_uploads import router as case_uploads_router
from app.api.routes.cases import router as cases_router
from app.api.routes.clinics import router as clinics_router
from app.api.routes.health import router as health_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.reports import router as reports_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(account_router, prefix="/account", tags=["account"])
api_router.include_router(audit_router, prefix="/audit-events", tags=["audit"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(case_design_router, prefix="/cases", tags=["case-design"])
api_router.include_router(case_delivery_router, prefix="/cases", tags=["case-delivery"])
api_router.include_router(case_production_router, prefix="/cases", tags=["case-production"])
api_router.include_router(case_returns_router, prefix="/cases", tags=["case-returns"])
api_router.include_router(case_uploads_router, prefix="/cases", tags=["case-files"])
api_router.include_router(case_transfers_router, prefix="/cases", tags=["case-transfers"])
api_router.include_router(cases_router, prefix="/cases", tags=["cases"])
api_router.include_router(clinics_router, prefix="/clinics", tags=["clinics"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
