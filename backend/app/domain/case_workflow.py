from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.models import RoleCode


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


class CaseWorkflowError(ValueError):
    pass


class InvalidCaseTransitionError(CaseWorkflowError):
    pass


class CaseActionDeniedError(CaseWorkflowError):
    pass


class CaseReasonRequiredError(CaseWorkflowError):
    pass


TRANSITIONS: dict[tuple[CaseStatus, CaseAction], CaseStatus] = {
    (CaseStatus.DRAFT, CaseAction.SUBMIT): CaseStatus.MANAGER_REVIEW,
    (CaseStatus.MANAGER_REVISION_REQUESTED, CaseAction.SUBMIT): CaseStatus.MANAGER_REVIEW,
    (CaseStatus.RESCAN_REQUESTED, CaseAction.SUBMIT): CaseStatus.MANAGER_REVIEW,
    (CaseStatus.DRAFT, CaseAction.CANCEL): CaseStatus.CANCELLED,
    (CaseStatus.MANAGER_REVISION_REQUESTED, CaseAction.CANCEL): CaseStatus.CANCELLED,
    (CaseStatus.MANAGER_REVIEW, CaseAction.MANAGER_APPROVE): CaseStatus.LAB_DESIGN,
    (
        CaseStatus.MANAGER_REVIEW,
        CaseAction.MANAGER_REQUEST_REVISION,
    ): CaseStatus.MANAGER_REVISION_REQUESTED,
    (CaseStatus.MANAGER_REVIEW, CaseAction.MANAGER_REJECT): CaseStatus.MANAGER_REJECTED,
    (CaseStatus.LAB_DESIGN, CaseAction.UPLOAD_DESIGN): CaseStatus.DENTIST_REVIEW,
    (
        CaseStatus.DESIGN_REVISION_REQUESTED,
        CaseAction.UPLOAD_DESIGN,
    ): CaseStatus.DENTIST_REVIEW,
    (
        CaseStatus.DENTIST_REVIEW,
        CaseAction.DENTIST_APPROVE_DESIGN,
    ): CaseStatus.READY_FOR_PRODUCTION,
    (
        CaseStatus.DENTIST_REVIEW,
        CaseAction.DENTIST_REQUEST_DESIGN_REVISION,
    ): CaseStatus.DESIGN_REVISION_REQUESTED,
    (
        CaseStatus.READY_FOR_PRODUCTION,
        CaseAction.START_PRODUCTION,
    ): CaseStatus.IN_PRODUCTION,
    (
        CaseStatus.REPRODUCTION_REQUESTED,
        CaseAction.START_PRODUCTION,
    ): CaseStatus.IN_PRODUCTION,
    (
        CaseStatus.IN_PRODUCTION,
        CaseAction.COMPLETE_PRODUCTION,
    ): CaseStatus.PRODUCTION_COMPLETED,
    (CaseStatus.PRODUCTION_COMPLETED, CaseAction.SHIP): CaseStatus.SHIPPED,
    (CaseStatus.SHIPPED, CaseAction.CONFIRM_DELIVERY): CaseStatus.DELIVERED,
    (
        CaseStatus.DELIVERED,
        CaseAction.REGISTER_RETURN_RECEIVED,
    ): CaseStatus.RETURN_REVIEW,
    (
        CaseStatus.RETURN_REVIEW,
        CaseAction.DECIDE_REPRODUCTION,
    ): CaseStatus.REPRODUCTION_REQUESTED,
    (CaseStatus.RETURN_REVIEW, CaseAction.DECIDE_RESCAN): CaseStatus.RESCAN_REQUESTED,
}


ACTION_ROLES: dict[CaseAction, frozenset[RoleCode]] = {
    CaseAction.SUBMIT: frozenset(
        {RoleCode.DENTIST, RoleCode.MANAGING_DENTIST, RoleCode.CLINIC_STAFF}
    ),
    CaseAction.CANCEL: frozenset(
        {RoleCode.DENTIST, RoleCode.MANAGING_DENTIST, RoleCode.CLINIC_STAFF}
    ),
    CaseAction.MANAGER_APPROVE: frozenset({RoleCode.MANAGING_DENTIST}),
    CaseAction.MANAGER_REQUEST_REVISION: frozenset({RoleCode.MANAGING_DENTIST}),
    CaseAction.MANAGER_REJECT: frozenset({RoleCode.MANAGING_DENTIST}),
    CaseAction.UPLOAD_DESIGN: frozenset({RoleCode.TECHNICIAN}),
    CaseAction.DENTIST_APPROVE_DESIGN: frozenset({RoleCode.DENTIST, RoleCode.MANAGING_DENTIST}),
    CaseAction.DENTIST_REQUEST_DESIGN_REVISION: frozenset(
        {RoleCode.DENTIST, RoleCode.MANAGING_DENTIST}
    ),
    CaseAction.START_PRODUCTION: frozenset({RoleCode.TECHNICIAN}),
    CaseAction.COMPLETE_PRODUCTION: frozenset({RoleCode.TECHNICIAN}),
    CaseAction.SHIP: frozenset({RoleCode.TECHNICIAN}),
    CaseAction.CONFIRM_DELIVERY: frozenset({RoleCode.CLINIC_MANAGER, RoleCode.CLINIC_STAFF}),
    CaseAction.REGISTER_RETURN_RECEIVED: frozenset({RoleCode.TECHNICIAN}),
    CaseAction.DECIDE_REPRODUCTION: frozenset({RoleCode.MANAGING_DENTIST}),
    CaseAction.DECIDE_RESCAN: frozenset({RoleCode.MANAGING_DENTIST}),
}


REASON_REQUIRED_ACTIONS = frozenset(
    {
        CaseAction.CANCEL,
        CaseAction.MANAGER_REQUEST_REVISION,
        CaseAction.MANAGER_REJECT,
        CaseAction.DENTIST_REQUEST_DESIGN_REVISION,
        CaseAction.REGISTER_RETURN_RECEIVED,
        CaseAction.DECIDE_REPRODUCTION,
        CaseAction.DECIDE_RESCAN,
    }
)

CLINIC_SCOPED_ACTIONS = frozenset(
    action for action, roles in ACTION_ROLES.items() if RoleCode.TECHNICIAN not in roles
)

CASE_OWNER_ACTIONS = frozenset({CaseAction.SUBMIT, CaseAction.CANCEL})
DENTIST_OWNER_ACTIONS = frozenset(
    {CaseAction.DENTIST_APPROVE_DESIGN, CaseAction.DENTIST_REQUEST_DESIGN_REVISION}
)


@dataclass(frozen=True, slots=True)
class CaseActionContext:
    actor_user_id: UUID
    actor_roles: frozenset[RoleCode]
    actor_clinic_ids: frozenset[UUID]
    case_clinic_id: UUID
    case_created_by_user_id: UUID
    responsible_dentist_user_id: UUID
    reason: str | None = None


def next_case_status(current: CaseStatus, action: CaseAction) -> CaseStatus:
    try:
        return TRANSITIONS[(current, action)]
    except KeyError as error:
        raise InvalidCaseTransitionError(
            f"'{current}' durumunda '{action}' işlemi yapılamaz."
        ) from error


def authorize_case_action(action: CaseAction, context: CaseActionContext) -> None:
    allowed_roles = ACTION_ROLES[action]
    if context.actor_roles.isdisjoint(allowed_roles):
        raise CaseActionDeniedError("Bu rol vaka işlemini gerçekleştiremez.")

    if action in CLINIC_SCOPED_ACTIONS and context.case_clinic_id not in context.actor_clinic_ids:
        raise CaseActionDeniedError("Kullanıcı bu kliniğin vakasına erişemez.")

    if action in CASE_OWNER_ACTIONS and context.actor_user_id not in {
        context.case_created_by_user_id,
        context.responsible_dentist_user_id,
    }:
        raise CaseActionDeniedError(
            "Taslak yalnızca oluşturan kişi veya sorumlu hekimce yönetilir."
        )

    if (
        action in DENTIST_OWNER_ACTIONS
        and context.actor_user_id != context.responsible_dentist_user_id
    ):
        raise CaseActionDeniedError("Tasarım onayını yalnızca sorumlu hekim verebilir.")

    if action in REASON_REQUIRED_ACTIONS and not (context.reason or "").strip():
        raise CaseReasonRequiredError("Bu işlem için gerekçe zorunludur.")


def is_manager_self_approval(action: CaseAction, context: CaseActionContext) -> bool:
    return action == CaseAction.MANAGER_APPROVE and context.actor_user_id in {
        context.case_created_by_user_id,
        context.responsible_dentist_user_id,
    }


def locked_artifact_for(action: CaseAction) -> str | None:
    if action == CaseAction.MANAGER_APPROVE:
        return "scan"
    if action == CaseAction.DENTIST_APPROVE_DESIGN:
        return "design"
    return None
