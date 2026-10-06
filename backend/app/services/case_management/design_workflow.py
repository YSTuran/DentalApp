from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import (
    CaseAction,
    CaseApproval,
    CaseApprovalType,
    CaseDecision,
    CaseFileKind,
    CaseFileVersion,
    CaseStatus,
    DentalCase,
    MeshValidationStatus,
    User,
)
from app.schemas.case import DentistDecisionRequest
from app.services.audit import record_audit_event
from app.services.case_management.exceptions import CaseConflictError, CaseValidationError
from app.services.case_management.repository import add_history, load_case
from app.services.case_management.transitions import authorize_transition
from app.services.case_management.validation import validate_clinic
from app.services.case_notifications import create_case_notifications

DENTIST_DECISION_ACTIONS = {
    CaseDecision.APPROVED: CaseAction.DENTIST_APPROVE_DESIGN,
    CaseDecision.REVISION_REQUESTED: CaseAction.DENTIST_REQUEST_DESIGN_REVISION,
}

DENTIST_AUDIT_ACTIONS = {
    CaseDecision.APPROVED: "case.design_approved",
    CaseDecision.REVISION_REQUESTED: "case.design_revision_requested",
}


def _latest_design(case: DentalCase) -> CaseFileVersion:
    designs = [version for version in case.file_versions if version.kind == CaseFileKind.DESIGN]
    if not designs:
        raise CaseValidationError("case_design_required")
    return max(designs, key=lambda version: version.version_number)


def _validate_design_version(
    case: DentalCase,
    *,
    file_version_id: UUID,
) -> CaseFileVersion:
    design = _latest_design(case)
    if design.id != file_version_id:
        raise CaseConflictError("case_design_version_changed")
    if design.mesh_status != MeshValidationStatus.VALID:
        raise CaseValidationError(
            "case_design_not_valid",
            context={"mesh_status": design.mesh_status},
        )
    return design


def _require_manager_approval(case: DentalCase) -> None:
    if not any(
        approval.approval_type == CaseApprovalType.MANAGER_SCAN
        and approval.decision == CaseDecision.APPROVED
        for approval in case.approvals
    ):
        raise CaseConflictError("case_manager_approval_required")


def submit_design(
    db: Session,
    *,
    case_id: UUID,
    file_version_id: UUID,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = authorize_transition(case, actor, CaseAction.UPLOAD_DESIGN, reason=None)
    validate_clinic(db, case.clinic_id)
    _require_manager_approval(case)
    design = _validate_design_version(case, file_version_id=file_version_id)

    if any(
        approval.approval_type == CaseApprovalType.DENTIST_DESIGN
        and approval.decision == CaseDecision.APPROVED
        and approval.file_version_id == design.id
        for approval in case.approvals
    ):
        raise CaseValidationError("case_new_design_required")

    if case.status == CaseStatus.DESIGN_REVISION_REQUESTED:
        revision_requests = [
            approval
            for approval in case.approvals
            if approval.approval_type == CaseApprovalType.DENTIST_DESIGN
            and approval.decision == CaseDecision.REVISION_REQUESTED
        ]
        if revision_requests:
            latest_request = max(revision_requests, key=lambda item: item.sequence_number)
            if latest_request.file_version_id == design.id:
                raise CaseValidationError("case_design_revision_required")

    previous_status = case.status
    try:
        case.status = next_status
        add_history(
            db,
            case=case,
            actor=actor,
            action=CaseAction.UPLOAD_DESIGN.value,
            from_status=previous_status,
            to_status=next_status,
            reason=None,
        )
        record_audit_event(
            db,
            action="case.design_submitted",
            entity_type="case",
            entity_id=case.id,
            actor=actor,
            clinic_id=case.clinic_id,
            before={"status": previous_status},
            after={
                "status": next_status,
                "file_version_id": design.id,
                "version_number": design.version_number,
            },
            context={"source": "api"},
            request=request,
        )
        create_case_notifications(db, case=case, action="case.design_submitted", actor=actor)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return load_case(db, case.id)


def dentist_decide_design(
    db: Session,
    *,
    case_id: UUID,
    payload: DentistDecisionRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    action = DENTIST_DECISION_ACTIONS[payload.decision]
    next_status = authorize_transition(case, actor, action, reason=payload.reason)
    validate_clinic(db, case.clinic_id)
    _require_manager_approval(case)
    design = _validate_design_version(case, file_version_id=payload.file_version_id)

    if any(
        approval.approval_type == CaseApprovalType.DENTIST_DESIGN
        and approval.file_version_id == design.id
        for approval in case.approvals
    ):
        raise CaseConflictError("case_design_already_decided")

    previous_status = case.status
    approval = CaseApproval(
        case_id=case.id,
        approval_type=CaseApprovalType.DENTIST_DESIGN,
        decision=payload.decision,
        file_version_id=design.id,
        actor_user_id=actor.id,
        reason=payload.reason,
    )

    try:
        case.approvals.append(approval)
        case.status = next_status
        if payload.decision == CaseDecision.APPROVED:
            design.is_locked = True
        add_history(
            db,
            case=case,
            actor=actor,
            action=action.value,
            from_status=previous_status,
            to_status=next_status,
            reason=payload.reason,
        )
        audit_action = DENTIST_AUDIT_ACTIONS[payload.decision]
        record_audit_event(
            db,
            action=audit_action,
            entity_type="case",
            entity_id=case.id,
            actor=actor,
            clinic_id=case.clinic_id,
            reason=payload.reason,
            before={"status": previous_status},
            after={
                "status": next_status,
                "decision": payload.decision,
                "file_version_id": design.id,
                "file_version_locked": design.is_locked,
            },
            context={"source": "api", "approval_type": CaseApprovalType.DENTIST_DESIGN},
            request=request,
        )
        create_case_notifications(db, case=case, action=audit_action, actor=actor)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return load_case(db, case.id)
