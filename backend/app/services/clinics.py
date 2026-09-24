from uuid import UUID

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Clinic, RoleCode, User
from app.schemas.clinic import ClinicCreateRequest, ClinicUpdateRequest
from app.services.audit import record_audit_event
from app.services.authorization import has_clinic_role, has_global_role


class ClinicNotFoundError(Exception):
    pass


class ClinicAccessDeniedError(Exception):
    pass


class ClinicCodeConflictError(Exception):
    pass


class ClinicNoChangesError(Exception):
    pass


class ClinicStateConflictError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def clinic_snapshot(clinic: Clinic) -> dict[str, object]:
    return {
        "id": clinic.id,
        "code": clinic.code,
        "name": clinic.name,
        "address": clinic.address,
        "phone": clinic.phone,
        "is_active": clinic.is_active,
    }


def _require_system_admin(actor: User) -> None:
    if not has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        raise ClinicAccessDeniedError


def _code_exists(db: Session, code: str, *, exclude_id: UUID | None = None) -> bool:
    statement = select(Clinic.id).where(func.lower(Clinic.code) == code.lower())
    if exclude_id is not None:
        statement = statement.where(Clinic.id != exclude_id)
    return db.scalar(statement) is not None


def _raise_integrity_error(db: Session, error: IntegrityError) -> None:
    db.rollback()
    constraint_name = getattr(getattr(error, "orig", None), "diag", None)
    constraint_name = getattr(constraint_name, "constraint_name", None)
    if constraint_name == "uq_clinics_code_lower":
        raise ClinicCodeConflictError from error
    raise error


def list_visible_clinics(
    db: Session,
    *,
    actor: User,
    is_active: bool | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Clinic], int]:
    filters = []

    if not has_global_role(actor, RoleCode.SYSTEM_ADMIN):
        clinic_ids = {
            assignment.clinic_id
            for assignment in actor.role_assignments
            if assignment.is_active
            and assignment.role == RoleCode.CLINIC_MANAGER
            and assignment.clinic_id is not None
        }
        if not clinic_ids:
            raise ClinicAccessDeniedError
        filters.append(Clinic.id.in_(clinic_ids))

    if is_active is not None:
        filters.append(Clinic.is_active.is_(is_active))
    if search is not None and (normalized_search := search.strip()):
        filters.append(
            or_(
                Clinic.code.icontains(normalized_search, autoescape=True),
                Clinic.name.icontains(normalized_search, autoescape=True),
            )
        )

    total = db.scalar(select(func.count()).select_from(Clinic).where(*filters)) or 0
    clinics = db.scalars(
        select(Clinic)
        .where(*filters)
        .order_by(func.lower(Clinic.name), func.lower(Clinic.code))
        .limit(limit)
        .offset(offset)
    ).all()
    return list(clinics), total


def get_visible_clinic(db: Session, *, actor: User, clinic_id: UUID) -> Clinic:
    clinic = db.get(Clinic, clinic_id)
    if clinic is None:
        raise ClinicNotFoundError

    is_system_admin = has_global_role(actor, RoleCode.SYSTEM_ADMIN)
    is_clinic_manager = has_clinic_role(actor, clinic_id, RoleCode.CLINIC_MANAGER)
    if not is_system_admin and not is_clinic_manager:
        raise ClinicAccessDeniedError
    return clinic


def create_clinic(
    db: Session,
    *,
    payload: ClinicCreateRequest,
    actor: User,
    request: Request,
) -> Clinic:
    _require_system_admin(actor)
    if _code_exists(db, payload.code):
        raise ClinicCodeConflictError

    clinic = Clinic(
        code=payload.code,
        name=payload.name,
        address=payload.address,
        phone=payload.phone,
    )

    try:
        db.add(clinic)
        db.flush()
        record_audit_event(
            db,
            action="clinic.created",
            entity_type="clinic",
            entity_id=clinic.id,
            actor=actor,
            clinic_id=clinic.id,
            reason=payload.reason,
            after=clinic_snapshot(clinic),
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except IntegrityError as error:
        _raise_integrity_error(db, error)
    except Exception:
        db.rollback()
        raise

    db.refresh(clinic)
    return clinic


def update_clinic(
    db: Session,
    *,
    clinic_id: UUID,
    payload: ClinicUpdateRequest,
    actor: User,
    request: Request,
) -> Clinic:
    _require_system_admin(actor)
    clinic = db.get(Clinic, clinic_id)
    if clinic is None:
        raise ClinicNotFoundError

    provided_fields = payload.model_fields_set & {"code", "name", "address", "phone"}
    before: dict[str, object] = {}
    after: dict[str, object] = {}

    for field_name in provided_fields:
        old_value = getattr(clinic, field_name)
        new_value = getattr(payload, field_name)
        if old_value != new_value:
            before[field_name] = old_value
            after[field_name] = new_value

    if not after:
        raise ClinicNoChangesError
    if "code" in after and _code_exists(db, str(after["code"]), exclude_id=clinic.id):
        raise ClinicCodeConflictError

    try:
        for field_name, value in after.items():
            setattr(clinic, field_name, value)
        db.flush()
        record_audit_event(
            db,
            action="clinic.updated",
            entity_type="clinic",
            entity_id=clinic.id,
            actor=actor,
            clinic_id=clinic.id,
            reason=payload.reason,
            before=before,
            after=after,
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except IntegrityError as error:
        _raise_integrity_error(db, error)
    except Exception:
        db.rollback()
        raise

    db.refresh(clinic)
    return clinic


def change_clinic_status(
    db: Session,
    *,
    clinic_id: UUID,
    is_active: bool,
    reason: str,
    actor: User,
    request: Request,
) -> Clinic:
    _require_system_admin(actor)
    clinic = db.get(Clinic, clinic_id)
    if clinic is None:
        raise ClinicNotFoundError
    if clinic.is_active == is_active:
        detail = "clinic_already_active" if is_active else "clinic_already_inactive"
        raise ClinicStateConflictError(detail)

    previous_status = clinic.is_active
    try:
        clinic.is_active = is_active
        db.flush()
        record_audit_event(
            db,
            action="clinic.reactivated" if is_active else "clinic.deactivated",
            entity_type="clinic",
            entity_id=clinic.id,
            actor=actor,
            clinic_id=clinic.id,
            reason=reason,
            before={"is_active": previous_status},
            after={"is_active": is_active},
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(clinic)
    return clinic
