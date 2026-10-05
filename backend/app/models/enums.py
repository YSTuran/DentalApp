from enum import StrEnum


class RoleCode(StrEnum):
    SYSTEM_ADMIN = "system_admin"
    CLINIC_MANAGER = "clinic_manager"
    MANAGING_DENTIST = "managing_dentist"
    DENTIST = "dentist"
    CLINIC_STAFF = "clinic_staff"
    TECHNICIAN = "technician"

    @property
    def is_global(self) -> bool:
        return self in {self.SYSTEM_ADMIN, self.TECHNICIAN}


class ThemeMode(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class ColorPalette(StrEnum):
    DEFAULT = "default"
    OCEAN = "ocean"
    VIOLET = "violet"
    ARCTIC = "arctic"
    SAGE = "sage"
    GRAPHITE = "graphite"
    AMBER = "amber"
    BURGUNDY = "burgundy"
    CORAL = "coral"
    SEPIA = "sepia"
    HIGH_CONTRAST = "high_contrast"


class CaseStatus(StrEnum):
    DRAFT = "draft"
    MANAGER_REVIEW = "manager_review"
    MANAGER_REVISION_REQUESTED = "manager_revision_requested"
    MANAGER_REJECTED = "manager_rejected"
    LAB_DESIGN = "lab_design"
    DENTIST_REVIEW = "dentist_review"
    DESIGN_REVISION_REQUESTED = "design_revision_requested"
    READY_FOR_PRODUCTION = "ready_for_production"
    IN_PRODUCTION = "in_production"
    PRODUCTION_COMPLETED = "production_completed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    RETURN_REVIEW = "return_review"
    REPRODUCTION_REQUESTED = "reproduction_requested"
    RESCAN_REQUESTED = "rescan_requested"
    CANCELLED = "cancelled"


class CaseAction(StrEnum):
    SUBMIT = "submit"
    CANCEL = "cancel"
    MANAGER_APPROVE = "manager_approve"
    MANAGER_REQUEST_REVISION = "manager_request_revision"
    MANAGER_REJECT = "manager_reject"
    UPLOAD_DESIGN = "upload_design"
    DENTIST_APPROVE_DESIGN = "dentist_approve_design"
    DENTIST_REQUEST_DESIGN_REVISION = "dentist_request_design_revision"
    START_PRODUCTION = "start_production"
    COMPLETE_PRODUCTION = "complete_production"
    SHIP = "ship"
    CONFIRM_DELIVERY = "confirm_delivery"
    REGISTER_RETURN_RECEIVED = "register_return_received"
    DECIDE_REPRODUCTION = "decide_reproduction"
    DECIDE_RESCAN = "decide_rescan"


class CaseFileKind(StrEnum):
    SCAN = "scan"
    DESIGN = "design"


class MeshValidationStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    FAILED = "failed"


class UploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class CaseApprovalType(StrEnum):
    MANAGER_SCAN = "manager_scan"
    DENTIST_DESIGN = "dentist_design"


class CaseDecision(StrEnum):
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"
    REJECTED = "rejected"


class ReturnReasonCode(StrEnum):
    FIT_ISSUE = "fit_issue"
    DAMAGED = "damaged"
    MANUFACTURING_DEFECT = "manufacturing_defect"
    OTHER = "other"


class ReturnResolution(StrEnum):
    REPRODUCTION = "reproduction"
    RESCAN = "rescan"
