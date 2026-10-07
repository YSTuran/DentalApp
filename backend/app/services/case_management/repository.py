from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Sequence, select
from sqlalchemy.orm import Session, selectinload

from app.models import CaseStatus, CaseStatusHistory, DentalCase, User
from app.services.case_management.exceptions import CaseNotFoundError

CASE_NUMBER_SEQUENCE = Sequence("case_number_seq")
CASE_LOAD_OPTIONS = (
    selectinload(DentalCase.details),
    selectinload(DentalCase.file_versions),
    selectinload(DentalCase.approvals),
    selectinload(DentalCase.clinic),
    selectinload(DentalCase.responsible_dentist),
    selectinload(DentalCase.reproduction_source),
    selectinload(DentalCase.reproduction_case),
)


def load_case(db: Session, case_id: UUID, *, for_update: bool = False) -> DentalCase:
    statement = select(DentalCase).where(DentalCase.id == case_id).options(*CASE_LOAD_OPTIONS)
    if for_update:
        statement = statement.with_for_update()
    case = db.scalar(statement)
    if case is None:
        raise CaseNotFoundError
    return case


def next_case_number(db: Session) -> str:
    sequence_value = db.scalar(select(CASE_NUMBER_SEQUENCE.next_value()))
    if sequence_value is None:
        raise RuntimeError("Vaka numarası üretilemedi.")
    return f"VKA-{datetime.now(UTC).year}-{sequence_value:06d}"


def case_snapshot(case: DentalCase) -> dict[str, object]:
    return {
        "case_number": case.case_number,
        "clinic_id": case.clinic_id,
        "created_by_user_id": case.created_by_user_id,
        "responsible_dentist_user_id": case.responsible_dentist_user_id,
        "patient_code": {"is_set": case.patient_code_encrypted is not None},
        "patient_name": {"is_set": case.patient_name_encrypted is not None},
        "status": case.status,
        "appliance_type": case.details.appliance_type,
        "material": case.details.material,
        "tooth_numbers": {"count": len(case.details.tooth_numbers)},
        "special_notes": {"is_set": case.details.special_notes is not None},
        "extra_fields": {"count": len(case.details.extra_fields)},
    }


def add_history(
    db: Session,
    *,
    case: DentalCase,
    actor: User,
    action: str,
    from_status: CaseStatus | None,
    to_status: CaseStatus,
    reason: str | None,
) -> None:
    db.add(
        CaseStatusHistory(
            case_id=case.id,
            from_status=from_status,
            to_status=to_status,
            action=action,
            actor_user_id=actor.id,
            reason=reason,
        )
    )
