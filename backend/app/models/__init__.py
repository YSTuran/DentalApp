"""SQLAlchemy models imported here for Alembic discovery."""

from app.db.base import Base
from app.models.audit_event import AuditEvent
from app.models.case import (
    CaseApproval,
    CaseDetail,
    CaseFileVersion,
    CaseStatusHistory,
    CaseUploadSession,
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
    ReturnReasonCode,
    ReturnResolution,
    RoleCode,
    ThemeMode,
    UploadStatus,
)
from app.models.fulfillment import (
    DeliveryConfirmation,
    ProductionCompletion,
    ProductionRun,
    ReturnDecision,
    ReturnReceipt,
    Shipment,
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
    "CaseUploadSession",
    "Clinic",
    "ColorPalette",
    "DentalCase",
    "DeliveryConfirmation",
    "MeshValidationStatus",
    "ProductionCompletion",
    "ProductionRun",
    "RoleCode",
    "ReturnDecision",
    "ReturnReasonCode",
    "ReturnReceipt",
    "ReturnResolution",
    "Shipment",
    "ThemeMode",
    "UploadStatus",
    "User",
    "UserPreference",
    "UserRoleAssignment",
]
