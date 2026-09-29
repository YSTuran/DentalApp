from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    CaseFileKind,
    Clinic,
    DentalCase,
    MeshValidationStatus,
    RoleCode,
    User,
)
from app.services.authorization import has_clinic_role
from app.services.case_management.exceptions import CaseValidationError


def validate_clinic(db: Session, clinic_id: UUID) -> Clinic:
    clinic = db.get(Clinic, clinic_id)
    if clinic is None:
        raise CaseValidationError("case_clinic_not_found")
    if not clinic.is_active:
        raise CaseValidationError("case_clinic_inactive")
    return clinic


def validate_responsible_dentist(db: Session, user_id: UUID, clinic_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise CaseValidationError("case_responsible_dentist_invalid")
    if not has_clinic_role(
        user,
        clinic_id,
        RoleCode.DENTIST,
        RoleCode.MANAGING_DENTIST,
    ):
        raise CaseValidationError("case_responsible_dentist_invalid")
    return user


def validate_submit_requirements(case: DentalCase) -> None:
    missing_fields = []
    if not case.patient_code:
        missing_fields.append("patient_code")
    if not case.details.appliance_type:
        missing_fields.append("appliance_type")
    if not case.details.material:
        missing_fields.append("material")
    if not case.details.tooth_numbers:
        missing_fields.append("tooth_numbers")
    if missing_fields:
        raise CaseValidationError(
            "case_required_fields_missing",
            context={"fields": missing_fields},
        )

    scan_versions = [version for version in case.file_versions if version.kind == CaseFileKind.SCAN]
    if not scan_versions:
        raise CaseValidationError("case_scan_required")
    latest_scan = max(scan_versions, key=lambda version: version.version_number)
    if latest_scan.mesh_status != MeshValidationStatus.VALID:
        raise CaseValidationError(
            "case_scan_not_valid",
            context={"mesh_status": latest_scan.mesh_status},
        )
