from uuid import uuid4

import pytest

from app.domain.case_workflow import (
    TRANSITIONS,
    CaseAction,
    CaseActionContext,
    CaseActionDeniedError,
    CaseReasonRequiredError,
    CaseStatus,
    InvalidCaseTransitionError,
    authorize_case_action,
    is_manager_self_approval,
    locked_artifact_for,
    next_case_status,
)
from app.models import RoleCode


def context_for(
    role: RoleCode,
    *,
    actor_is_creator: bool = True,
    actor_is_dentist: bool = True,
    same_clinic: bool = True,
    reason: str | None = "Gerekli açıklama",
) -> CaseActionContext:
    actor_id = uuid4()
    case_clinic_id = uuid4()
    return CaseActionContext(
        actor_user_id=actor_id,
        actor_role_assignments=frozenset(
            {(role, None if role.is_global else case_clinic_id)}
            if same_clinic or role.is_global
            else {(role, uuid4())}
        ),
        case_clinic_id=case_clinic_id,
        case_created_by_user_id=actor_id if actor_is_creator else uuid4(),
        responsible_dentist_user_id=actor_id if actor_is_dentist else uuid4(),
        reason=reason,
    )


@pytest.mark.parametrize(("state_action", "expected"), TRANSITIONS.items())
def test_every_declared_transition_reaches_expected_status(
    state_action: tuple[CaseStatus, CaseAction],
    expected: CaseStatus,
) -> None:
    assert next_case_status(*state_action) == expected


def test_two_approvals_cannot_be_skipped() -> None:
    with pytest.raises(InvalidCaseTransitionError):
        next_case_status(CaseStatus.MANAGER_REVIEW, CaseAction.START_PRODUCTION)
    with pytest.raises(InvalidCaseTransitionError):
        next_case_status(CaseStatus.DENTIST_REVIEW, CaseAction.START_PRODUCTION)


def test_design_approval_is_limited_to_responsible_dentist() -> None:
    context = context_for(RoleCode.DENTIST, actor_is_dentist=False)

    with pytest.raises(CaseActionDeniedError, match="sorumlu hekim"):
        authorize_case_action(CaseAction.DENTIST_APPROVE_DESIGN, context)


def test_clinic_staff_can_submit_case_but_cannot_approve_design() -> None:
    context = context_for(RoleCode.CLINIC_STAFF, actor_is_dentist=False)

    authorize_case_action(CaseAction.SUBMIT, context)
    with pytest.raises(CaseActionDeniedError):
        authorize_case_action(CaseAction.DENTIST_APPROVE_DESIGN, context)


def test_manager_cannot_review_case_from_another_clinic() -> None:
    context = context_for(RoleCode.MANAGING_DENTIST, same_clinic=False)

    with pytest.raises(CaseActionDeniedError, match="vaka kliniğinde"):
        authorize_case_action(CaseAction.MANAGER_APPROVE, context)


def test_role_from_one_clinic_cannot_authorize_action_in_another_clinic() -> None:
    actor_id = uuid4()
    manager_clinic_id = uuid4()
    staff_clinic_id = uuid4()
    context = CaseActionContext(
        actor_user_id=actor_id,
        actor_role_assignments=frozenset(
            {
                (RoleCode.MANAGING_DENTIST, manager_clinic_id),
                (RoleCode.CLINIC_STAFF, staff_clinic_id),
            }
        ),
        case_clinic_id=staff_clinic_id,
        case_created_by_user_id=uuid4(),
        responsible_dentist_user_id=uuid4(),
        reason=None,
    )

    with pytest.raises(CaseActionDeniedError, match="vaka kliniğinde"):
        authorize_case_action(CaseAction.MANAGER_APPROVE, context)


def test_system_admin_does_not_inherit_clinical_approval() -> None:
    context = context_for(RoleCode.SYSTEM_ADMIN)

    with pytest.raises(CaseActionDeniedError):
        authorize_case_action(CaseAction.MANAGER_APPROVE, context)


def test_negative_decisions_require_reason() -> None:
    context = context_for(RoleCode.MANAGING_DENTIST, reason="  ")

    with pytest.raises(CaseReasonRequiredError):
        authorize_case_action(CaseAction.MANAGER_REQUEST_REVISION, context)


def test_manager_self_approval_is_marked() -> None:
    own_case = context_for(RoleCode.MANAGING_DENTIST)
    another_case = context_for(
        RoleCode.MANAGING_DENTIST,
        actor_is_creator=False,
        actor_is_dentist=False,
    )

    assert is_manager_self_approval(CaseAction.MANAGER_APPROVE, own_case) is True
    assert is_manager_self_approval(CaseAction.MANAGER_APPROVE, another_case) is False


def test_approvals_lock_the_reviewed_artifact() -> None:
    assert locked_artifact_for(CaseAction.MANAGER_APPROVE) == "scan"
    assert locked_artifact_for(CaseAction.DENTIST_APPROVE_DESIGN) == "design"
    assert locked_artifact_for(CaseAction.SHIP) is None


def test_delivery_is_confirmed_by_branch_role() -> None:
    authorize_case_action(
        CaseAction.CONFIRM_DELIVERY,
        context_for(RoleCode.CLINIC_MANAGER),
    )
    authorize_case_action(
        CaseAction.CONFIRM_DELIVERY,
        context_for(RoleCode.CLINIC_STAFF),
    )
    with pytest.raises(CaseActionDeniedError):
        authorize_case_action(
            CaseAction.CONFIRM_DELIVERY,
            context_for(RoleCode.TECHNICIAN),
        )


def test_return_decision_routes_to_reproduction_or_new_scan() -> None:
    assert (
        next_case_status(CaseStatus.RETURN_REVIEW, CaseAction.DECIDE_REPRODUCTION)
        == CaseStatus.REPRODUCTION_REQUESTED
    )
    assert (
        next_case_status(CaseStatus.RETURN_REVIEW, CaseAction.DECIDE_RESCAN)
        == CaseStatus.RESCAN_REQUESTED
    )
