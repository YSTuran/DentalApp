from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CaseApprovalType,
    CaseDecision,
    CaseFileKind,
    CaseFileVersion,
    CaseStatus,
    Clinic,
    DentalCase,
    MeshValidationStatus,
    ProductionRun,
    ReturnDecision,
    ReturnReceipt,
    ReturnResolution,
    RoleCode,
    Shipment,
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


def validate_submit_requirements(db: Session, case: DentalCase) -> None:
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

    if case.status == CaseStatus.MANAGER_REVISION_REQUESTED:
        revision_requests = [
            approval
            for approval in case.approvals
            if approval.approval_type == CaseApprovalType.MANAGER_SCAN
            and approval.decision == CaseDecision.REVISION_REQUESTED
        ]
        if revision_requests:
            latest_request = max(
                revision_requests,
                key=lambda approval: approval.sequence_number,
            )
            if latest_scan.id == latest_request.file_version_id:
                raise CaseValidationError("case_scan_revision_required")

    if case.status == CaseStatus.RESCAN_REQUESTED:
        rescan_decision = db.scalar(
            select(ReturnDecision)
            .join(ReturnReceipt, ReturnReceipt.id == ReturnDecision.return_receipt_id)
            .join(Shipment, Shipment.id == ReturnReceipt.shipment_id)
            .join(ProductionRun, ProductionRun.id == Shipment.production_run_id)
            .where(
                ProductionRun.case_id == case.id,
                ReturnDecision.resolution == ReturnResolution.RESCAN,
            )
            .order_by(ReturnDecision.decided_at.desc())
        )
        source_scan = (
            db.get(CaseFileVersion, rescan_decision.source_scan_file_version_id)
            if rescan_decision is not None
            else None
        )
        if (
            source_scan is None
            or latest_scan.id == source_scan.id
            or latest_scan.version_number <= source_scan.version_number
        ):
            raise CaseValidationError("case_rescan_required")
