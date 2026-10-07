import logging
from collections.abc import Callable
from uuid import UUID

from fastapi import Request
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    RoleCode,
    User,
    UserClinicAssignment,
    UserPreference,
    UserRoleAssignment,
)
from app.schemas.user_management import (
    RoleAssignmentCreateRequest,
    RoleAssignmentUpdateRequest,
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
from app.services.user_errors import (
    FirebaseSyncError,
    RoleAssignmentNotFoundError,
    UserAccessDeniedError,
    UserConflictError,
    UserNotFoundError,
    UserValidationError,
)
from app.services.user_role_policy import (
    reject_system_admin_assignment as _reject_system_admin_assignment,
)
from app.services.user_role_policy import validate_initial_clinics
from app.services.user_role_policy import (
    validate_role_compatibility as _validate_role_compatibility,
)

logger = logging.getLogger(__name__)
CLINIC_MANAGER_VISIBLE_ROLES = {RoleCode.DENTIST, RoleCode.MANAGING_DENTIST}
SYSTEM_ADMIN_MUTATION_LOCK_KEY = 4_428_861_106_564_001_101


def _load_user(db: Session, user_id: UUID) -> User:
    user = db.scalar(
        select(User)
        .options(
            selectinload(User.role_assignments),
            selectinload(User.clinic_assignments),
        )
        .where(User.id == user_id)
    )
    if user is None:
        raise UserNotFoundError
    return user


def _manager_clinic_ids(actor: User) -> set[UUID]:
    if not any(
        assignment.is_active and assignment.role == RoleCode.CLINIC_MANAGER
        for assignment in actor.role_assignments
    ):
        return set()
    return {
        assignment.clinic_id
        for assignment in actor.clinic_assignments
        if assignment.is_active
    }


def _require_system_admin(actor: User) -> None:
    if not has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        raise UserAccessDeniedError


def _raise_role_integrity_error(error: IntegrityError) -> None:
    constraint_name = getattr(
        getattr(getattr(error, "orig", None), "diag", None), "constraint_name", None
    )
    if constraint_name in {
        "ck_user_role_assignments_single_active_role",
        "uq_user_role_assignment_active_user",
    }:
        raise UserValidationError("conflicting_active_role") from error
    raise UserConflictError("role_assignment_exists") from error


def _clear_active_clinic_for_global_role(db: Session, user: User, role: RoleCode) -> bool:
    if not role.is_global:
        return False
    preference = db.get(UserPreference, user.id)
    if preference is None or preference.active_clinic_id is None:
        return False
    preference.active_clinic_id = None
    return True


def _active_system_admin_count(db: Session) -> int:
    return (
        db.scalar(
            select(func.count(func.distinct(User.id)))
            .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
            .where(
                User.is_active.is_(True),
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.role == RoleCode.SYSTEM_ADMIN,
            )
        )
        or 0
    )


def _lock_system_admin_mutation(db: Session) -> None:
    """Serialize operations that could remove the final active system admin."""
    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": SYSTEM_ADMIN_MUTATION_LOCK_KEY},
    )


def _has_active_system_admin_role(user: User) -> bool:
    return any(
        assignment.is_active
        and assignment.role == RoleCode.SYSTEM_ADMIN
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
            and_(
                User.role_assignments.any(
                    and_(
                        UserRoleAssignment.is_active.is_(True),
                        UserRoleAssignment.role.in_(CLINIC_MANAGER_VISIBLE_ROLES),
                    )
                ),
                User.clinic_assignments.any(
                    and_(
                        UserClinicAssignment.is_active.is_(True),
                        UserClinicAssignment.clinic_id.in_(visible_clinics),
                    )
                ),
            )
        )
    elif clinic_id is not None:
        filters.append(
            User.clinic_assignments.any(
                and_(
                    UserClinicAssignment.is_active.is_(True),
                    UserClinicAssignment.clinic_id == clinic_id,
                )
            )
        )

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
        .options(
            selectinload(User.role_assignments),
            selectinload(User.clinic_assignments),
        )
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
    has_visible_role = any(
        assignment.is_active
        and assignment.role in CLINIC_MANAGER_VISIBLE_ROLES
        for assignment in user.role_assignments
    )
    shares_clinic = any(
        assignment.is_active and assignment.clinic_id in manager_clinics
        for assignment in user.clinic_assignments
    )
    if not has_visible_role or not shares_clinic:
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
    shares_clinic = any(
        assignment.is_active and assignment.clinic_id in manager_clinics
        for assignment in user.clinic_assignments
    )
    if not shares_clinic:
        return []
    return [
        assignment
        for assignment in user.role_assignments
        if assignment.is_active and assignment.role in CLINIC_MANAGER_VISIBLE_ROLES
    ]


def list_visible_clinic_assignments(
    *,
    actor: User,
    user: User,
) -> list[UserClinicAssignment]:
    if has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        return list(user.clinic_assignments)
    manager_clinics = _manager_clinic_ids(actor)
    return [
        assignment
        for assignment in user.clinic_assignments
        if assignment.is_active and assignment.clinic_id in manager_clinics
    ]


def create_user(
    db: Session,
    *,
    payload: UserCreateRequest,
    actor: User,
    request: Request,
) -> tuple[User, str]:
    _require_system_admin(actor)
    _reject_system_admin_assignment(payload.role)
    clinics = validate_initial_clinics(
        db,
        role=payload.role,
        clinic_ids=payload.clinic_ids,
    )
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
        is_active=True,
    )
    user.role_assignments = [assignment]
    user.clinic_assignments = [
        UserClinicAssignment(clinic_id=clinic.id, is_active=True)
        for clinic in clinics
    ]

    try:
        db.add(user)
        db.flush()
        record_audit_event(
            db,
            action="user.created",
            entity_type="user",
            entity_id=user.id,
            actor=actor,
            clinic_id=clinics[0].id if len(clinics) == 1 else None,
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
            clinic_id=None,
            reason=payload.reason,
            after={
                "user_id": user.id,
                "role": assignment.role,
                "is_active": True,
            },
            context={"source": "api"},
            request=request,
        )
        for clinic_assignment in user.clinic_assignments:
            record_audit_event(
                db,
                action="user.clinic_assigned",
                entity_type="user_clinic_assignment",
                entity_id=clinic_assignment.id,
                actor=actor,
                clinic_id=clinic_assignment.clinic_id,
                reason=payload.reason,
                after={
                    "user_id": user.id,
                    "clinic_id": clinic_assignment.clinic_id,
                    "is_active": True,
                },
                context={"source": "api", "during_user_creation": True},
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
    if not is_active and _has_active_system_admin_role(user):
        _lock_system_admin_mutation(db)
        if _active_system_admin_count(db) <= 1:
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
    _reject_system_admin_assignment(payload.role)
    _validate_role_compatibility(db, user_id=user.id, role=payload.role)

    existing = db.scalar(
        select(UserRoleAssignment)
        .where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role == payload.role,
        )
        .order_by(UserRoleAssignment.updated_at.desc(), UserRoleAssignment.id)
        .limit(1)
    )
    if existing is not None:
        raise UserConflictError("role_assignment_exists")

    assignment = UserRoleAssignment(
        user_id=user.id,
        role=payload.role,
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
            clinic_id=None,
            reason=payload.reason,
            after={
                "user_id": user.id,
                "role": assignment.role,
                "is_active": True,
            },
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        _raise_role_integrity_error(error)
    except Exception:
        db.rollback()
        raise

    db.refresh(assignment)
    return assignment


def replace_role_assignment(
    db: Session,
    *,
    user_id: UUID,
    assignment_id: UUID,
    payload: RoleAssignmentUpdateRequest,
    actor: User,
    request: Request,
) -> UserRoleAssignment:
    _require_system_admin(actor)
    user = _load_user(db, user_id)
    if not user.is_active:
        raise UserConflictError("user_inactive")

    current_assignment = db.scalar(
        select(UserRoleAssignment)
        .where(
            UserRoleAssignment.id == assignment_id,
            UserRoleAssignment.user_id == user.id,
        )
        .with_for_update()
    )
    if current_assignment is None:
        raise RoleAssignmentNotFoundError
    if not current_assignment.is_active:
        raise UserConflictError("role_assignment_inactive")
    if current_assignment.role == RoleCode.SYSTEM_ADMIN:
        raise UserValidationError("system_admin_assignment_not_allowed")

    _reject_system_admin_assignment(payload.role)
    _validate_role_compatibility(
        db,
        user_id=user.id,
        role=payload.role,
        exclude_assignment_id=current_assignment.id,
    )
    if current_assignment.role == payload.role:
        raise UserConflictError("role_assignment_no_changes")

    replacement = db.scalar(
        select(UserRoleAssignment)
        .where(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role == payload.role,
        )
        .order_by(UserRoleAssignment.updated_at.desc(), UserRoleAssignment.id)
        .limit(1)
        .with_for_update()
    )
    previous_replacement_status = replacement.is_active if replacement is not None else None
    before = {
        "assignment_id": current_assignment.id,
        "role": current_assignment.role,
        "is_active": True,
    }

    try:
        current_assignment.is_active = False
        if replacement is None:
            replacement = UserRoleAssignment(
                user_id=user.id,
                role=payload.role,
                is_active=True,
            )
            db.add(replacement)
        else:
            replacement.is_active = True

        db.flush()
        active_clinic_cleared = _clear_active_clinic_for_global_role(
            db,
            user,
            payload.role,
        )
        record_audit_event(
            db,
            action="user.role_changed",
            entity_type="user_role_assignment",
            entity_id=current_assignment.id,
            actor=actor,
            clinic_id=None,
            reason=payload.reason,
            before=before,
            after={
                "assignment_id": replacement.id,
                "role": replacement.role,
                "is_active": True,
            },
            context={
                "source": "api",
                "user_id": user.id,
                "replacement_reactivated": previous_replacement_status is False,
                "replacement_already_active": previous_replacement_status is True,
                "active_clinic_cleared": active_clinic_cleared,
            },
            request=request,
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        _raise_role_integrity_error(error)
    except Exception:
        db.rollback()
        raise

    db.refresh(replacement)
    return replacement


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
        _validate_role_compatibility(
            db,
            user_id=user.id,
            role=assignment.role,
            exclude_assignment_id=assignment.id,
        )
    elif assignment.role == RoleCode.SYSTEM_ADMIN and user.is_active:
        if user.id == actor.id:
            raise UserConflictError("cannot_remove_own_system_admin_role")
        _lock_system_admin_mutation(db)
        if _active_system_admin_count(db) <= 1:
            raise UserConflictError("last_system_admin")

    previous_status = assignment.is_active
    try:
        assignment.is_active = is_active
        db.flush()
        active_clinic_cleared = (
            _clear_active_clinic_for_global_role(db, user, assignment.role)
            if is_active
            else False
        )
        record_audit_event(
            db,
            action="user.role_reactivated" if is_active else "user.role_deactivated",
            entity_type="user_role_assignment",
            entity_id=assignment.id,
            actor=actor,
            clinic_id=None,
            reason=reason,
            before={"is_active": previous_status},
            after={"is_active": is_active},
            context={
                "source": "api",
                "user_id": user.id,
                "active_clinic_cleared": active_clinic_cleared,
            },
            request=request,
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        _raise_role_integrity_error(error)
    except Exception:
        db.rollback()
        raise

    db.refresh(assignment)
    return assignment
