import logging
from collections.abc import Callable
from uuid import UUID

from fastapi import Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import Clinic, RoleCode, User, UserRoleAssignment
from app.schemas.user_management import (
    RoleAssignmentCreateRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.services.audit import record_audit_event
from app.services.authorization import has_global_role
from app.services.firebase_identity import (
    FirebaseIdentityConflictError,
    FirebaseIdentityError,
    create_identity,
    delete_identity,
    generate_temporary_password,
    set_identity_disabled,
    update_identity_name,
)

logger = logging.getLogger(__name__)
CLINIC_MANAGER_VISIBLE_ROLES = {RoleCode.DENTIST, RoleCode.MANAGING_DENTIST}


class UserNotFoundError(Exception):
    pass


class RoleAssignmentNotFoundError(Exception):
    pass


class UserAccessDeniedError(Exception):
    pass


class UserConflictError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class UserValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class FirebaseSyncError(Exception):
    def __init__(self, detail: str = "firebase_service_unavailable") -> None:
        self.detail = detail
        super().__init__(detail)


def _load_user(db: Session, user_id: UUID) -> User:
    user = db.scalar(
        select(User).options(selectinload(User.role_assignments)).where(User.id == user_id)
    )
    if user is None:
        raise UserNotFoundError
    return user


def _manager_clinic_ids(actor: User) -> set[UUID]:
    return {
        assignment.clinic_id
        for assignment in actor.role_assignments
        if assignment.is_active
        and assignment.role == RoleCode.CLINIC_MANAGER
        and assignment.clinic_id is not None
    }


def _require_system_admin(actor: User) -> None:
    if not has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        raise UserAccessDeniedError


def _validate_role_scope(
    db: Session,
    *,
    role: RoleCode,
    clinic_id: UUID | None,
) -> Clinic | None:
    if role.is_global:
        if clinic_id is not None:
            raise UserValidationError("global_role_cannot_have_clinic")
        return None
    if clinic_id is None:
        raise UserValidationError("clinic_role_requires_clinic")

    clinic = db.get(Clinic, clinic_id)
    if clinic is None:
        raise UserValidationError("clinic_not_found")
    if not clinic.is_active:
        raise UserConflictError("clinic_inactive")
    return clinic


def _active_system_admin_count(db: Session) -> int:
    return (
        db.scalar(
            select(func.count(func.distinct(User.id)))
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .where(
                User.is_active.is_(True),
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.role == RoleCode.SYSTEM_ADMIN,
                UserRoleAssignment.clinic_id.is_(None),
            )
        )
        or 0
    )


def _has_active_system_admin_role(user: User) -> bool:
    return any(
        assignment.is_active
        and assignment.role == RoleCode.SYSTEM_ADMIN
        and assignment.clinic_id is None
        for assignment in user.role_assignments
    )


def _run_compensation(action: Callable[[], None]) -> None:
    try:
        action()
    except FirebaseIdentityError as error:
        logger.exception("Firebase telafi işlemi başarısız oldu")
        raise FirebaseSyncError("firebase_compensation_failed") from error


def list_visible_users(
    db: Session,
    *,
    actor: User,
    search: str | None,
    is_active: bool | None,
    role: RoleCode | None,
    clinic_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    filters = []
    is_system_admin = has_global_role(actor, RoleCode.SYSTEM_ADMIN)

    if not is_system_admin:
        manager_clinics = _manager_clinic_ids(actor)
        if not manager_clinics:
            raise UserAccessDeniedError
        if clinic_id is not None and clinic_id not in manager_clinics:
            raise UserAccessDeniedError
        visible_clinics = {clinic_id} if clinic_id is not None else manager_clinics
        filters.append(
            User.role_assignments.any(
                and_(
                    UserRoleAssignment.is_active.is_(True),
                    UserRoleAssignment.clinic_id.in_(visible_clinics),
                    UserRoleAssignment.role.in_(CLINIC_MANAGER_VISIBLE_ROLES),
                )
            )
        )
    elif clinic_id is not None:
        filters.append(User.role_assignments.any(UserRoleAssignment.clinic_id == clinic_id))

    if is_active is not None:
        filters.append(User.is_active.is_(is_active))
    if role is not None:
        if not is_system_admin and role not in CLINIC_MANAGER_VISIBLE_ROLES:
            raise UserAccessDeniedError
        filters.append(
            User.role_assignments.any(
                and_(
                    UserRoleAssignment.role == role,
                    UserRoleAssignment.is_active.is_(True),
                )
            )
        )
    if search is not None and (normalized_search := search.strip()):
        filters.append(
            or_(
                User.email.icontains(normalized_search, autoescape=True),
                User.full_name.icontains(normalized_search, autoescape=True),
            )
        )

    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    users = db.scalars(
        select(User)
        .options(selectinload(User.role_assignments))
        .where(*filters)
        .order_by(func.lower(User.full_name), func.lower(User.email))
        .limit(limit)
        .offset(offset)
    ).all()
    return list(users), total


def get_visible_user(db: Session, *, actor: User, user_id: UUID) -> User:
    user = _load_user(db, user_id)
    if has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        return user

    manager_clinics = _manager_clinic_ids(actor)
    is_visible_doctor = any(
        assignment.is_active
        and assignment.clinic_id in manager_clinics
        and assignment.role in CLINIC_MANAGER_VISIBLE_ROLES
        for assignment in user.role_assignments
    )
    if not is_visible_doctor:
        raise UserAccessDeniedError
    return user


def list_visible_role_assignments(
    *,
    actor: User,
    user: User,
) -> list[UserRoleAssignment]:
    if has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        return list(user.role_assignments)

    manager_clinics = _manager_clinic_ids(actor)
    return [
        assignment
        for assignment in user.role_assignments
        if assignment.is_active
        and assignment.clinic_id in manager_clinics
        and assignment.role in CLINIC_MANAGER_VISIBLE_ROLES
    ]


def create_user(
    db: Session,
    *,
    payload: UserCreateRequest,
    actor: User,
    request: Request,
) -> tuple[User, str]:
    _require_system_admin(actor)
    _validate_role_scope(db, role=payload.role, clinic_id=payload.clinic_id)
    if db.scalar(select(User.id).where(func.lower(User.email) == payload.email.lower())):
        raise UserConflictError("user_email_exists")

    temporary_password = generate_temporary_password()
    try:
        firebase_uid = create_identity(
            email=payload.email,
            full_name=payload.full_name,
            password=temporary_password,
        )
    except FirebaseIdentityConflictError as error:
        raise UserConflictError("user_email_exists") from error
    except FirebaseIdentityError as error:
        raise FirebaseSyncError from error

    user = User(
        firebase_uid=firebase_uid,
        email=payload.email,
        full_name=payload.full_name,
        is_active=True,
    )
    assignment = UserRoleAssignment(
        role=payload.role,
        clinic_id=payload.clinic_id,
        is_active=True,
    )
    user.role_assignments = [assignment]

    try:
        db.add(user)
        db.flush()
        record_audit_event(
            db,
            action="user.created",
            entity_type="user",
            entity_id=user.id,
            actor=actor,
            clinic_id=payload.clinic_id,
            reason=payload.reason,
            after={
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
            },
            context={"source": "api", "provider": "firebase"},
            request=request,
        )
        record_audit_event(
            db,
            action="user.role_assigned",
            entity_type="user_role_assignment",
            entity_id=assignment.id,
            actor=actor,
            clinic_id=payload.clinic_id,
            reason=payload.reason,
            after={
                "user_id": user.id,
                "role": assignment.role,
                "clinic_id": assignment.clinic_id,
                "is_active": True,
            },
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except Exception as error:
        db.rollback()
        _run_compensation(lambda: delete_identity(firebase_uid))
        constraint_name = getattr(
            getattr(getattr(error, "orig", None), "diag", None), "constraint_name", None
        )
        if isinstance(error, IntegrityError) and constraint_name == "uq_users_email_lower":
            raise UserConflictError("user_email_exists") from error
        raise

    db.refresh(user)
    return user, temporary_password


def update_user(
    db: Session,
    *,
    user_id: UUID,
    payload: UserUpdateRequest,
    actor: User,
    request: Request,
) -> User:
    _require_system_admin(actor)
    user = _load_user(db, user_id)
    old_name = user.full_name
    if old_name == payload.full_name:
        raise UserConflictError("user_no_changes")

    try:
        update_identity_name(user.firebase_uid, payload.full_name)
    except FirebaseIdentityError as error:
        raise FirebaseSyncError("firebase_identity_missing") from error

    try:
        user.full_name = payload.full_name
        db.flush()
        record_audit_event(
            db,
            action="user.updated",
            entity_type="user",
            entity_id=user.id,
            actor=actor,
            reason=payload.reason,
            before={"full_name": old_name},
            after={"full_name": user.full_name},
            context={"source": "api", "provider": "firebase"},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        _run_compensation(lambda: update_identity_name(user.firebase_uid, old_name))
        raise

    db.refresh(user)
    return user


def change_user_status(
    db: Session,
    *,
    user_id: UUID,
    is_active: bool,
    reason: str,
    actor: User,
    request: Request,
) -> User:
    _require_system_admin(actor)
    user = _load_user(db, user_id)
    if user.is_active == is_active:
        detail = "user_already_active" if is_active else "user_already_inactive"
        raise UserConflictError(detail)
    if not is_active and user.id == actor.id:
        raise UserConflictError("cannot_deactivate_self")
    if (
        not is_active
        and _has_active_system_admin_role(user)
        and _active_system_admin_count(db) <= 1
    ):
        raise UserConflictError("last_system_admin")

    try:
        set_identity_disabled(user.firebase_uid, disabled=not is_active)
    except FirebaseIdentityError as error:
        raise FirebaseSyncError("firebase_identity_missing") from error

    old_status = user.is_active
    try:
        user.is_active = is_active
        db.flush()
        record_audit_event(
            db,
            action="user.reactivated" if is_active else "user.deactivated",
            entity_type="user",
            entity_id=user.id,
            actor=actor,
            reason=reason,
            before={"is_active": old_status},
            after={"is_active": is_active},
            context={"source": "api", "provider": "firebase"},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        _run_compensation(lambda: set_identity_disabled(user.firebase_uid, disabled=not old_status))
        raise

    db.refresh(user)
    return user


def assign_role(
    db: Session,
    *,
    user_id: UUID,
    payload: RoleAssignmentCreateRequest,
    actor: User,
    request: Request,
) -> UserRoleAssignment:
    _require_system_admin(actor)
    user = _load_user(db, user_id)
    if not user.is_active:
        raise UserConflictError("user_inactive")
    _validate_role_scope(db, role=payload.role, clinic_id=payload.clinic_id)

    existing = db.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role == payload.role,
            UserRoleAssignment.clinic_id.is_(payload.clinic_id)
            if payload.clinic_id is None
            else UserRoleAssignment.clinic_id == payload.clinic_id,
        )
    )
    if existing is not None:
        raise UserConflictError("role_assignment_exists")

    assignment = UserRoleAssignment(
        user_id=user.id,
        role=payload.role,
        clinic_id=payload.clinic_id,
        is_active=True,
    )
    try:
        db.add(assignment)
        db.flush()
        record_audit_event(
            db,
            action="user.role_assigned",
            entity_type="user_role_assignment",
            entity_id=assignment.id,
            actor=actor,
            clinic_id=payload.clinic_id,
            reason=payload.reason,
            after={
                "user_id": user.id,
                "role": assignment.role,
                "clinic_id": assignment.clinic_id,
                "is_active": True,
            },
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise UserConflictError("role_assignment_exists") from error
    except Exception:
        db.rollback()
        raise

    db.refresh(assignment)
    return assignment


def change_role_status(
    db: Session,
    *,
    user_id: UUID,
    assignment_id: UUID,
    is_active: bool,
    reason: str,
    actor: User,
    request: Request,
) -> UserRoleAssignment:
    _require_system_admin(actor)
    user = _load_user(db, user_id)
    assignment = db.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.id == assignment_id,
            UserRoleAssignment.user_id == user.id,
        )
    )
    if assignment is None:
        raise RoleAssignmentNotFoundError
    if assignment.is_active == is_active:
        detail = "role_already_active" if is_active else "role_already_inactive"
        raise UserConflictError(detail)
    if is_active:
        if not user.is_active:
            raise UserConflictError("user_inactive")
        _validate_role_scope(db, role=assignment.role, clinic_id=assignment.clinic_id)
    elif assignment.role == RoleCode.SYSTEM_ADMIN and user.is_active:
        if user.id == actor.id:
            raise UserConflictError("cannot_remove_own_system_admin_role")
        if _active_system_admin_count(db) <= 1:
            raise UserConflictError("last_system_admin")

    previous_status = assignment.is_active
    try:
        assignment.is_active = is_active
        db.flush()
        record_audit_event(
            db,
            action="user.role_reactivated" if is_active else "user.role_deactivated",
            entity_type="user_role_assignment",
            entity_id=assignment.id,
            actor=actor,
            clinic_id=assignment.clinic_id,
            reason=reason,
            before={"is_active": previous_status},
            after={"is_active": is_active},
            context={"source": "api", "user_id": user.id},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(assignment)
    return assignment
