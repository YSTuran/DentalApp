from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CaseAction,
    CaseApprovalType,
    CaseDecision,
    CaseFileKind,
    CaseFileVersion,
    DentalCase,
    ProductionRun,
    Shipment,
    User,
)
from app.services.audit import record_audit_event
from app.services.case_management.exceptions import CaseConflictError
from app.services.case_management.repository import add_history
from app.services.case_notifications import create_case_notifications


def approved_design(case: DentalCase, *, expected_id: UUID | None = None) -> CaseFileVersion:
    designs = [file for file in case.file_versions if file.kind == CaseFileKind.DESIGN]
    if not designs:
        raise CaseConflictError("case_approved_design_required")
    design = max(designs, key=lambda file: file.version_number)
    if expected_id is not None and design.id != expected_id:
        raise CaseConflictError("case_design_version_changed")
    has_manager_approval = any(
        approval.approval_type == CaseApprovalType.MANAGER_SCAN
        and approval.decision == CaseDecision.APPROVED
        for approval in case.approvals
    )
    has_design_approval = any(
        approval.approval_type == CaseApprovalType.DENTIST_DESIGN
        and approval.decision == CaseDecision.APPROVED
        and approval.file_version_id == design.id
        for approval in case.approvals
    )
    if not has_manager_approval or not has_design_approval or not design.is_locked:
        raise CaseConflictError("case_two_approvals_required")
    return design


def production_run_for_case(
    db: Session,
    *,
    case_id: UUID,
    production_run_id: UUID,
) -> ProductionRun:
    run = db.scalar(
        select(ProductionRun).where(
            ProductionRun.id == production_run_id,
            ProductionRun.case_id == case_id,
        )
    )
    if run is None:
        raise CaseConflictError("case_production_run_changed")
    return run


def shipment_for_case(
    db: Session,
    *,
    case_id: UUID,
    shipment_id: UUID,
) -> Shipment:
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise CaseConflictError("case_shipment_changed")
    production_run_for_case(
        db,
        case_id=case_id,
        production_run_id=shipment.production_run_id,
    )
    return shipment


def apply_operation_transition(
    db: Session,
    *,
    case: DentalCase,
    actor: User,
    action: CaseAction,
    next_status,
    audit_action: str,
    reason: str | None,
    audit_after: dict[str, Any],
    request: Request,
) -> None:
    previous_status = case.status
    case.status = next_status
    add_history(
        db,
        case=case,
        actor=actor,
        action=action.value,
        from_status=previous_status,
        to_status=next_status,
        reason=reason,
    )
    record_audit_event(
        db,
        action=audit_action,
        entity_type="case",
        entity_id=case.id,
        actor=actor,
        clinic_id=case.clinic_id,
        reason=reason,
        before={"status": previous_status},
        after={"status": next_status, **audit_after},
        context={"source": "api"},
        request=request,
    )
    create_case_notifications(db, case=case, action=audit_action, actor=actor)
