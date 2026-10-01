from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.domain.case_workflow import (
    CaseActionContext,
    CaseActionDeniedError,
    CaseReasonRequiredError,
    InvalidCaseTransitionError,
    authorize_case_action,
    next_case_status,
)
from app.models import CaseAction, CaseStatus, DentalCase, User
from app.services.audit import record_audit_event
from app.services.case_management.access import actor_role_assignments
from app.services.case_management.exceptions import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseValidationError,
)
from app.services.case_management.repository import add_history, load_case
from app.services.case_management.validation import validate_clinic, validate_submit_requirements


def _action_context(case: DentalCase, actor: User, *, reason: str | None) -> CaseActionContext:
    return CaseActionContext(
        actor_user_id=actor.id,
        actor_role_assignments=actor_role_assignments(actor),
        case_clinic_id=case.clinic_id,
        case_created_by_user_id=case.created_by_user_id,
        responsible_dentist_user_id=case.responsible_dentist_user_id,
        reason=reason,
    )


def _authorize_transition(
    case: DentalCase,
    actor: User,
    action: CaseAction,
    *,
    reason: str | None,
) -> CaseStatus:
    try:
        authorize_case_action(action, _action_context(case, actor, reason=reason))
        return next_case_status(case.status, action)
    except CaseActionDeniedError as error:
        raise CaseAccessDeniedError from error
    except CaseReasonRequiredError as error:
        raise CaseValidationError("case_reason_required") from error
    except InvalidCaseTransitionError as error:
        raise CaseConflictError("case_invalid_transition") from error


def submit_case(
    db: Session,
    *,
    case_id: UUID,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = _authorize_transition(case, actor, CaseAction.SUBMIT, reason=None)
    validate_clinic(db, case.clinic_id)
    validate_submit_requirements(case)
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
    next_status = _authorize_transition(case, actor, CaseAction.CANCEL, reason=reason)
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
        db.commit()
    except Exception:
        db.rollback()
        raise

    return load_case(db, case.id)
