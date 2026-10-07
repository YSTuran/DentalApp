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
from app.models.case_transfer import CaseTransfer
from app.models.case_wait_alert import CaseWaitAlert
from app.models.clinic import Clinic
from app.models.clinic_assignment import UserClinicAssignment
from app.models.email_outbox import EmailOutbox
from app.models.enums import (
    CaseAction,
    CaseApprovalType,
    CaseDecision,
    CaseFileKind,
    CaseStatus,
    CaseTransferStatus,
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
from app.models.notification import Notification
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
    "CaseTransfer",
    "CaseTransferStatus",
    "CaseUploadSession",
    "CaseWaitAlert",
    "Clinic",
    "ColorPalette",
    "DentalCase",
    "DeliveryConfirmation",
    "EmailOutbox",
    "MeshValidationStatus",
    "Notification",
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
    "UserClinicAssignment",
    "UserPreference",
    "UserRoleAssignment",
]
