from copy import deepcopy

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import CaseDetail, CaseStatus, DentalCase, User
from app.services.audit import record_audit_event
from app.services.case_management.patient_data import (
    get_patient_code,
    get_patient_name,
    set_patient_identity,
)
from app.services.case_management.repository import add_history, case_snapshot, next_case_number


def create_reproduction_case(
    db: Session,
    *,
    source_case: DentalCase,
    actor: User,
    reason: str,
    request: Request,
) -> DentalCase:
    reproduction = DentalCase(
        case_number=next_case_number(db),
        clinic_id=source_case.clinic_id,
        created_by_user_id=source_case.created_by_user_id,
        responsible_dentist_user_id=source_case.responsible_dentist_user_id,
        reproduction_source_case_id=source_case.id,
        status=CaseStatus.DRAFT,
        details=CaseDetail(
            appliance_type=source_case.details.appliance_type,
            material=source_case.details.material,
            tooth_numbers=deepcopy(source_case.details.tooth_numbers),
            special_notes=source_case.details.special_notes,
            extra_fields=deepcopy(source_case.details.extra_fields),
        ),
    )
    set_patient_identity(
        reproduction,
        patient_code=get_patient_code(source_case),
        patient_name=get_patient_name(source_case),
    )
    db.add(reproduction)
    db.flush()
    add_history(
        db,
        case=reproduction,
        actor=actor,
        action="create_reproduction",
        from_status=None,
        to_status=CaseStatus.DRAFT,
        reason=reason,
    )
    record_audit_event(
        db,
        action="case.created_from_return",
        entity_type="case",
        entity_id=reproduction.id,
        actor=actor,
        clinic_id=reproduction.clinic_id,
        reason=reason,
        after=case_snapshot(reproduction),
        context={"source": "return_decision", "source_case_id": source_case.id},
        request=request,
    )
    return reproduction
