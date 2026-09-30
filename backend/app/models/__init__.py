"""SQLAlchemy models imported here for Alembic discovery."""

from app.db.base import Base
from app.models.audit_event import AuditEvent
from app.models.case import (
    CaseApproval,
    CaseDetail,
    CaseFileVersion,
    CaseStatusHistory,
    DentalCase,
)
from app.models.clinic import Clinic
from app.models.enums import (
    CaseAction,
    CaseApprovalType,
    CaseDecision,
    CaseFileKind,
    CaseStatus,
    ColorPalette,
    MeshValidationStatus,
    RoleCode,
    ThemeMode,
)
from app.models.role_assignment import UserRoleAssignment
from app.models.user import User
from app.models.user_preference import UserPreference

__all__ = [
    "AuditEvent",
    "Base",
    "CaseAction",
    "CaseApproval",
    "CaseApprovalType",
    "CaseDecision",
    "CaseDetail",
    "CaseFileKind",
    "CaseFileVersion",
    "CaseStatus",
    "CaseStatusHistory",
    "Clinic",
    "ColorPalette",
    "DentalCase",
    "MeshValidationStatus",
    "RoleCode",
    "ThemeMode",
    "User",
    "UserPreference",
    "UserRoleAssignment",
]
