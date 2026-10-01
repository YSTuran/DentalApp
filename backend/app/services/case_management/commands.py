from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import CaseDetail, CaseStatus, DentalCase, User
from app.schemas.case import CaseCreateRequest, CaseUpdateRequest
from app.services.audit import record_audit_event
from app.services.case_management.access import require_case_visibility, require_create_access
from app.services.case_management.exceptions import CaseAccessDeniedError, CaseConflictError
from app.services.case_management.repository import (
    add_history,
    case_snapshot,
    load_case,
    next_case_number,
)
from app.services.case_management.validation import (
    validate_clinic,
    validate_responsible_dentist,
)

EDITABLE_CASE_STATUSES = frozenset(
    {CaseStatus.DRAFT, CaseStatus.MANAGER_REVISION_REQUESTED, CaseStatus.RESCAN_REQUESTED}
)
CASE_UPDATE_FIELDS = {
    "responsible_dentist_user_id",
    "patient_code",
    "patient_name",
    "appliance_type",
    "material",
    "tooth_numbers",
    "special_notes",
    "extra_fields",
}
CASE_MAIN_FIELDS = {
    "responsible_dentist_user_id",
    "patient_code",
    "patient_name",
}


def create_case(
    db: Session,
    *,
    payload: CaseCreateRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    require_create_access(actor, payload.clinic_id)
    validate_clinic(db, payload.clinic_id)
    validate_responsible_dentist(
        db,
        payload.responsible_dentist_user_id,
        payload.clinic_id,
    )

    case = DentalCase(
        case_number=next_case_number(db),
        clinic_id=payload.clinic_id,
        created_by_user_id=actor.id,
        responsible_dentist_user_id=payload.responsible_dentist_user_id,
        patient_code=payload.patient_code,
        patient_name=payload.patient_name,
        status=CaseStatus.DRAFT,
        details=CaseDetail(
            appliance_type=payload.appliance_type,
            material=payload.material,
            tooth_numbers=payload.tooth_numbers,
            special_notes=payload.special_notes,
            extra_fields=payload.extra_fields,
        ),
    )

    try:
        db.add(case)
        db.flush()
        add_history(
            db,
            case=case,
            actor=actor,
            action="create",
            from_status=None,
            to_status=CaseStatus.DRAFT,
            reason=payload.reason,
        )
        record_audit_event(
            db,
            action="case.created",
            entity_type="case",
            entity_id=case.id,
            actor=actor,
            clinic_id=case.clinic_id,
            reason=payload.reason,
            after=case_snapshot(case),
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return load_case(db, case.id)


def update_case(
    db: Session,
    *,
    case_id: UUID,
    payload: CaseUpdateRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    require_case_visibility(actor, case)
    if actor.id not in {case.created_by_user_id, case.responsible_dentist_user_id}:
        raise CaseAccessDeniedError
    validate_clinic(db, case.clinic_id)
    if case.status not in EDITABLE_CASE_STATUSES:
        raise CaseConflictError("case_not_editable")

    provided_fields = payload.model_fields_set & CASE_UPDATE_FIELDS
    if "responsible_dentist_user_id" in provided_fields:
        validate_responsible_dentist(
            db,
            payload.responsible_dentist_user_id,
            case.clinic_id,
        )

    before: dict[str, object] = {}
    after: dict[str, object] = {}
    for field_name in provided_fields:
        target = case if field_name in CASE_MAIN_FIELDS else case.details
        old_value = getattr(target, field_name)
        new_value = getattr(payload, field_name)
        if old_value != new_value:
            before[field_name] = old_value
            after[field_name] = new_value

    if not after:
        raise CaseConflictError("case_no_changes")

    try:
        for field_name, value in after.items():
            target = case if field_name in CASE_MAIN_FIELDS else case.details
            setattr(target, field_name, value)
        db.flush()
        record_audit_event(
            db,
            action="case.updated",
            entity_type="case",
            entity_id=case.id,
            actor=actor,
            clinic_id=case.clinic_id,
            reason=payload.reason,
            before=before,
            after=after,
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return load_case(db, case.id)
