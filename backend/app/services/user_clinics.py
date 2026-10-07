from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Clinic, RoleCode, User, UserClinicAssignment, UserPreference
from app.services.audit import record_audit_event
from app.services.authorization import has_global_role
from app.services.user_errors import (
    ClinicAssignmentNotFoundError,
    UserAccessDeniedError,
    UserConflictError,
    UserNotFoundError,
    UserValidationError,
)


def _require_system_admin(actor: User) -> None:
    if not has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        raise UserAccessDeniedError


def _load_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError
    return user


def _active_clinic(db: Session, clinic_id: UUID) -> Clinic:
    clinic = db.get(Clinic, clinic_id)
    if clinic is None:
        raise UserValidationError("clinic_not_found")
    if not clinic.is_active:
        raise UserConflictError("clinic_inactive")
    return clinic


def _require_clinic_eligible_role(user: User) -> None:
    active_roles = [
        assignment.role for assignment in user.role_assignments if assignment.is_active
    ]
    if not active_roles:
        raise UserConflictError("active_role_required")
    if any(role.is_global for role in active_roles):
        raise UserValidationError("global_role_cannot_have_clinic")


def assign_clinic(
    db: Session,
    *,
    user_id: UUID,
    clinic_id: UUID,
    reason: str | None,
    actor: User,
    request: Request,
) -> UserClinicAssignment:
    _require_system_admin(actor)
    user = _load_user(db, user_id)
    if not user.is_active:
        raise UserConflictError("user_inactive")
    _require_clinic_eligible_role(user)
    _active_clinic(db, clinic_id)
    existing = db.scalar(
        select(UserClinicAssignment).where(
            UserClinicAssignment.user_id == user.id,
            UserClinicAssignment.clinic_id == clinic_id,
        )
    )
    if existing is not None:
        raise UserConflictError("clinic_assignment_exists")

    assignment = UserClinicAssignment(
        user_id=user.id,
        clinic_id=clinic_id,
        is_active=True,
    )
    try:
        db.add(assignment)
        db.flush()
        record_audit_event(
            db,
            action="user.clinic_assigned",
            entity_type="user_clinic_assignment",
            entity_id=assignment.id,
            actor=actor,
            clinic_id=clinic_id,
            reason=reason,
            after={"user_id": user.id, "clinic_id": clinic_id, "is_active": True},
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise UserConflictError("clinic_assignment_exists") from error
    except Exception:
        db.rollback()
        raise
    db.refresh(assignment)
    return assignment


def change_clinic_assignment_status(
    db: Session,
    *,
    user_id: UUID,
    assignment_id: UUID,
    is_active: bool,
    reason: str,
    actor: User,
    request: Request,
) -> UserClinicAssignment:
    _require_system_admin(actor)
    user = _load_user(db, user_id)
    assignment = db.scalar(
        select(UserClinicAssignment)
        .where(
            UserClinicAssignment.id == assignment_id,
            UserClinicAssignment.user_id == user.id,
        )
        .with_for_update()
    )
    if assignment is None:
        raise ClinicAssignmentNotFoundError
    if assignment.is_active == is_active:
        detail = (
            "clinic_assignment_already_active"
            if is_active
            else "clinic_assignment_already_inactive"
        )
        raise UserConflictError(detail)
    if is_active:
        if not user.is_active:
            raise UserConflictError("user_inactive")
        _require_clinic_eligible_role(user)
        _active_clinic(db, assignment.clinic_id)

    previous = assignment.is_active
    try:
        assignment.is_active = is_active
        preference = db.get(UserPreference, user.id)
        active_clinic_cleared = bool(
            not is_active
            and preference is not None
            and preference.active_clinic_id == assignment.clinic_id
        )
        if active_clinic_cleared:
            preference.active_clinic_id = None
        db.flush()
        record_audit_event(
            db,
            action="user.clinic_reactivated" if is_active else "user.clinic_deactivated",
            entity_type="user_clinic_assignment",
            entity_id=assignment.id,
            actor=actor,
            clinic_id=assignment.clinic_id,
            reason=reason,
            before={"is_active": previous},
            after={"is_active": is_active},
            context={
                "source": "api",
                "user_id": user.id,
                "active_clinic_cleared": active_clinic_cleared,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(assignment)
    return assignment
