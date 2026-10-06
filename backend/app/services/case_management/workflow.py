from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.domain.case_workflow import (
    is_manager_self_approval,
)
from app.models import (
    CaseAction,
    CaseApproval,
    CaseApprovalType,
    CaseDecision,
    CaseFileKind,
    DentalCase,
    MeshValidationStatus,
    User,
)
from app.schemas.case import ManagerDecisionRequest
from app.services.audit import record_audit_event
from app.services.case_management.exceptions import (
    CaseConflictError,
    CaseValidationError,
)
from app.services.case_management.repository import add_history, load_case
from app.services.case_management.transitions import action_context, authorize_transition
from app.services.case_management.validation import validate_clinic, validate_submit_requirements
from app.services.case_notifications import create_case_notifications

MANAGER_DECISION_ACTIONS = {
    CaseDecision.APPROVED: CaseAction.MANAGER_APPROVE,
    CaseDecision.REVISION_REQUESTED: CaseAction.MANAGER_REQUEST_REVISION,
    CaseDecision.REJECTED: CaseAction.MANAGER_REJECT,
}

MANAGER_AUDIT_ACTIONS = {
    CaseDecision.APPROVED: "case.manager_approved",
    CaseDecision.REVISION_REQUESTED: "case.manager_revision_requested",
    CaseDecision.REJECTED: "case.manager_rejected",
}


def submit_case(
    db: Session,
    *,
    case_id: UUID,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = authorize_transition(case, actor, CaseAction.SUBMIT, reason=None)
    validate_clinic(db, case.clinic_id)
    validate_submit_requirements(db, case)
    previous_status = case.status

    try:
        case.status = next_status
        case.submitted_at = datetime.now(UTC)
        add_history(
            db,
            case=case,
            actor=actor,
            action=CaseAction.SUBMIT.value,
            from_status=previous_status,
            to_status=next_status,
            reason=None,
        )
        record_audit_event(
            db,
            action="case.submitted",
            entity_type="case",
            entity_id=case.id,
            actor=actor,
            clinic_id=case.clinic_id,
            before={"status": previous_status},
            after={"status": next_status, "submitted_at": case.submitted_at},
            context={"source": "api"},
            request=request,
        )
        create_case_notifications(db, case=case, action="case.submitted", actor=actor)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return load_case(db, case.id)


def cancel_case(
    db: Session,
    *,
    case_id: UUID,
    reason: str,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = authorize_transition(case, actor, CaseAction.CANCEL, reason=reason)
    previous_status = case.status

    try:
        case.status = next_status
        case.cancelled_at = datetime.now(UTC)
        add_history(
            db,
            case=case,
            actor=actor,
            action=CaseAction.CANCEL.value,
            from_status=previous_status,
            to_status=next_status,
            reason=reason,
        )
        record_audit_event(
            db,
            action="case.cancelled",
            entity_type="case",
            entity_id=case.id,
            actor=actor,
            clinic_id=case.clinic_id,
            reason=reason,
            before={"status": previous_status},
            after={"status": next_status, "cancelled_at": case.cancelled_at},
            context={"source": "api"},
            request=request,
        )
        create_case_notifications(db, case=case, action="case.cancelled", actor=actor)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return load_case(db, case.id)


def manager_decide_case(
    db: Session,
    *,
    case_id: UUID,
    payload: ManagerDecisionRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    action = MANAGER_DECISION_ACTIONS[payload.decision]
    next_status = authorize_transition(case, actor, action, reason=payload.reason)
    validate_clinic(db, case.clinic_id)

    scan_versions = [
        version for version in case.file_versions if version.kind == CaseFileKind.SCAN
    ]
    if not scan_versions:
        raise CaseValidationError("case_scan_required")
    latest_scan = max(scan_versions, key=lambda version: version.version_number)
    if latest_scan.id != payload.file_version_id:
        raise CaseConflictError("case_scan_version_changed")
    if any(
        approval.approval_type == CaseApprovalType.MANAGER_SCAN
        and approval.file_version_id == latest_scan.id
        for approval in case.approvals
    ):
        raise CaseConflictError("case_scan_already_decided")
    if latest_scan.mesh_status != MeshValidationStatus.VALID:
        raise CaseValidationError(
            "case_scan_not_valid",
            context={"mesh_status": latest_scan.mesh_status},
        )

    previous_status = case.status
    self_approval = is_manager_self_approval(
        action,
        action_context(case, actor, reason=payload.reason),
    )
    approval = CaseApproval(
        case_id=case.id,
        approval_type=CaseApprovalType.MANAGER_SCAN,
        decision=payload.decision,
        file_version_id=latest_scan.id,
        actor_user_id=actor.id,
        reason=payload.reason,
        is_self_approval=self_approval,
    )

    try:
        case.approvals.append(approval)
        case.status = next_status
        if payload.decision == CaseDecision.APPROVED:
            latest_scan.is_locked = True
        add_history(
            db,
            case=case,
            actor=actor,
            action=action.value,
            from_status=previous_status,
            to_status=next_status,
            reason=payload.reason,
        )
        audit_action = MANAGER_AUDIT_ACTIONS[payload.decision]
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
                "file_version_id": latest_scan.id,
                "file_version_locked": latest_scan.is_locked,
                "is_self_approval": self_approval,
            },
            context={"source": "api", "approval_type": CaseApprovalType.MANAGER_SCAN},
            request=request,
        )
        create_case_notifications(db, case=case, action=audit_action, actor=actor)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return load_case(db, case.id)
