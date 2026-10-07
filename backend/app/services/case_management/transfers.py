from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CaseTransfer,
    CaseTransferStatus,
    RoleCode,
    User,
    UserRoleAssignment,
)
from app.schemas.case_transfer import CaseTransferResponse
from app.services.audit import record_audit_event
from app.services.authorization import has_clinic_role
from app.services.case_management.access import require_case_visibility
from app.services.case_management.exceptions import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
)
from app.services.case_management.queries import TERMINAL_CASE_STATUSES
from app.services.case_management.repository import load_case
from app.services.case_management.validation import validate_responsible_dentist
from app.services.notification_delivery import add_user_notification

TRANSFER_REQUEST_ROLES = (RoleCode.CLINIC_MANAGER, RoleCode.MANAGING_DENTIST)
TRANSFER_LOAD_OPTIONS = (
    selectinload(CaseTransfer.from_dentist),
    selectinload(CaseTransfer.to_dentist),
    selectinload(CaseTransfer.requested_by),
    selectinload(CaseTransfer.decided_by),
)


def _can_request_transfer(actor: User, clinic_id: UUID) -> bool:
    return has_clinic_role(actor, clinic_id, *TRANSFER_REQUEST_ROLES)


def _serialize(transfer: CaseTransfer) -> CaseTransferResponse:
    return CaseTransferResponse(
        id=transfer.id,
        case_id=transfer.case_id,
        from_dentist_user_id=transfer.from_dentist_user_id,
        from_dentist_name=transfer.from_dentist.full_name,
        to_dentist_user_id=transfer.to_dentist_user_id,
        to_dentist_name=transfer.to_dentist.full_name,
        requested_by_user_id=transfer.requested_by_user_id,
        requested_by_name=transfer.requested_by.full_name,
        decided_by_user_id=transfer.decided_by_user_id,
        decided_by_name=transfer.decided_by.full_name if transfer.decided_by else None,
        status=transfer.status,
        request_reason=transfer.request_reason,
        decision_reason=transfer.decision_reason,
        requested_at=transfer.requested_at,
        decided_at=transfer.decided_at,
    )


def _load_transfer(db: Session, transfer_id: UUID, *, for_update: bool) -> CaseTransfer:
    statement = (
        select(CaseTransfer)
        .where(CaseTransfer.id == transfer_id)
        .options(*TRANSFER_LOAD_OPTIONS)
    )
    if for_update:
        statement = statement.with_for_update()
    transfer = db.scalar(statement)
    if transfer is None:
        raise CaseNotFoundError
    return transfer


def _notify(
    db: Session,
    *,
    recipients: set[UUID],
    actor: User,
    case_id: UUID,
    kind: str,
    title: str,
    message: str,
) -> None:
    recipients.discard(actor.id)
    for recipient_id in recipients:
        add_user_notification(
            db,
            recipient_user_id=recipient_id,
            actor_user_id=actor.id,
            case_id=case_id,
            kind=kind,
            title=title,
            message=message,
            target_path=f"/vakalar/{case_id}",
        )


def list_transfer_options(db: Session, *, actor: User, case_id: UUID) -> list[User]:
    case = load_case(db, case_id)
    require_case_visibility(actor, case)
    if not _can_request_transfer(actor, case.clinic_id):
        raise CaseAccessDeniedError
    return list(
        db.scalars(
            select(User)
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .where(
                User.is_active.is_(True),
                User.id != case.responsible_dentist_user_id,
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.clinic_id == case.clinic_id,
                UserRoleAssignment.role.in_({RoleCode.DENTIST, RoleCode.MANAGING_DENTIST}),
            )
            .distinct()
            .order_by(User.full_name, User.id)
        ).all()
    )


def list_case_transfers(
    db: Session,
    *,
    actor: User,
    case_id: UUID,
) -> list[CaseTransferResponse]:
    case = load_case(db, case_id)
    require_case_visibility(actor, case)
    transfers = db.scalars(
        select(CaseTransfer)
        .where(CaseTransfer.case_id == case_id)
        .options(*TRANSFER_LOAD_OPTIONS)
        .order_by(CaseTransfer.requested_at.desc(), CaseTransfer.id)
    ).all()
    return [_serialize(item) for item in transfers]


def request_case_transfer(
    db: Session,
    *,
    case_id: UUID,
    to_dentist_user_id: UUID,
    reason: str,
    actor: User,
    request: Request,
) -> CaseTransferResponse:
    case = load_case(db, case_id, for_update=True)
    require_case_visibility(actor, case)
    if not _can_request_transfer(actor, case.clinic_id):
        raise CaseAccessDeniedError
    if case.status in TERMINAL_CASE_STATUSES:
        raise CaseConflictError("case_transfer_not_active")
    if to_dentist_user_id == case.responsible_dentist_user_id:
        raise CaseConflictError("case_transfer_same_dentist")
    target = validate_responsible_dentist(db, to_dentist_user_id, case.clinic_id)

    transfer = CaseTransfer(
        case_id=case.id,
        from_dentist_user_id=case.responsible_dentist_user_id,
        to_dentist_user_id=target.id,
        requested_by_user_id=actor.id,
        status=CaseTransferStatus.PENDING,
        request_reason=reason,
    )
    try:
        db.add(transfer)
        db.flush()
        record_audit_event(
            db,
            action="case.transfer_requested",
            entity_type="case_transfer",
            entity_id=transfer.id,
            actor=actor,
            clinic_id=case.clinic_id,
            reason=reason,
            after={
                "case_id": case.id,
                "from_dentist_user_id": transfer.from_dentist_user_id,
                "to_dentist_user_id": transfer.to_dentist_user_id,
                "status": transfer.status,
            },
            context={"source": "api"},
            request=request,
        )
        _notify(
            db,
            recipients={target.id},
            actor=actor,
            case_id=case.id,
            kind="case.transfer_requested",
            title="Vaka devri onayınızı bekliyor",
            message=f"{case.case_number} numaralı vaka size devredilmek isteniyor.",
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise CaseConflictError("case_transfer_pending_exists") from error
    except Exception:
        db.rollback()
        raise
    return _serialize(_load_transfer(db, transfer.id, for_update=False))


def decide_case_transfer(
    db: Session,
    *,
    case_id: UUID,
    transfer_id: UUID,
    decision: CaseTransferStatus,
    reason: str | None,
    actor: User,
    request: Request,
) -> CaseTransferResponse:
    case = load_case(db, case_id, for_update=True)
    require_case_visibility(actor, case)
    transfer = _load_transfer(db, transfer_id, for_update=True)
    if transfer.case_id != case.id:
        raise CaseNotFoundError
    if transfer.status != CaseTransferStatus.PENDING:
        raise CaseConflictError("case_transfer_already_decided")
    if transfer.to_dentist_user_id != actor.id:
        raise CaseAccessDeniedError
    validate_responsible_dentist(db, actor.id, case.clinic_id)
    if decision == CaseTransferStatus.ACCEPTED and case.status in TERMINAL_CASE_STATUSES:
        raise CaseConflictError("case_transfer_not_active")
    if decision == CaseTransferStatus.ACCEPTED and (
        case.responsible_dentist_user_id != transfer.from_dentist_user_id
    ):
        raise CaseConflictError("case_transfer_source_changed")

    now = datetime.now(UTC)
    transfer.status = decision
    transfer.decision_reason = reason
    transfer.decided_by_user_id = actor.id
    transfer.decided_at = now
    previous_dentist_id = case.responsible_dentist_user_id
    if decision == CaseTransferStatus.ACCEPTED:
        case.responsible_dentist_user_id = actor.id

    try:
        db.flush()
        accepted = decision == CaseTransferStatus.ACCEPTED
        record_audit_event(
            db,
            action="case.transfer_accepted" if accepted else "case.transfer_rejected",
            entity_type="case_transfer",
            entity_id=transfer.id,
            actor=actor,
            clinic_id=case.clinic_id,
            reason=reason,
            before={
                "status": CaseTransferStatus.PENDING,
                "responsible_dentist_user_id": previous_dentist_id,
            },
            after={
                "status": decision,
                "responsible_dentist_user_id": case.responsible_dentist_user_id,
            },
            context={"source": "api", "case_id": case.id},
            request=request,
        )
        _notify(
            db,
            recipients={transfer.from_dentist_user_id, transfer.requested_by_user_id},
            actor=actor,
            case_id=case.id,
            kind="case.transfer_accepted" if accepted else "case.transfer_rejected",
            title="Vaka devri kabul edildi" if accepted else "Vaka devri reddedildi",
            message=(
                f"{case.case_number} numaralı vakanın sorumlu hekimi değiştirildi."
                if accepted
                else f"{case.case_number} numaralı vaka devir talebi reddedildi."
            ),
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _serialize(_load_transfer(db, transfer.id, for_update=False))
