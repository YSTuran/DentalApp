from app.api.dependencies.authorization import require_any_role
from app.models import RoleCode

case_access = require_any_role(
    RoleCode.SYSTEM_ADMIN,
    RoleCode.CLINIC_MANAGER,
    RoleCode.MANAGING_DENTIST,
    RoleCode.DENTIST,
    RoleCode.CLINIC_STAFF,
    RoleCode.TECHNICIAN,
)
