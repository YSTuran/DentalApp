from app.domain.case_workflow import (
    CaseActionContext,
    CaseActionDeniedError,
    CaseReasonRequiredError,
    InvalidCaseTransitionError,
    authorize_case_action,
    next_case_status,
)
from app.models import CaseAction, CaseStatus, DentalCase, User
from app.services.case_management.access import actor_role_assignments
from app.services.case_management.exceptions import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseValidationError,
)


def action_context(
    case: DentalCase,
    actor: User,
    *,
    reason: str | None,
) -> CaseActionContext:
    return CaseActionContext(
        actor_user_id=actor.id,
        actor_role_assignments=actor_role_assignments(actor),
        case_clinic_id=case.clinic_id,
        case_created_by_user_id=case.created_by_user_id,
        responsible_dentist_user_id=case.responsible_dentist_user_id,
        reason=reason,
    )


def authorize_transition(
    case: DentalCase,
    actor: User,
    action: CaseAction,
    *,
    reason: str | None,
) -> CaseStatus:
    try:
        authorize_case_action(action, action_context(case, actor, reason=reason))
        return next_case_status(case.status, action)
    except CaseActionDeniedError as error:
        raise CaseAccessDeniedError from error
    except CaseReasonRequiredError as error:
        raise CaseValidationError("case_reason_required") from error
    except InvalidCaseTransitionError as error:
        raise CaseConflictError("case_invalid_transition") from error
