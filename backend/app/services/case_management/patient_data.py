from uuid import uuid4

from app.core.patient_data import get_patient_data_cipher
from app.models import DentalCase


def set_patient_code(case: DentalCase, value: str | None) -> None:
    _ensure_case_id(case)
    if value is None:
        case.patient_code_encrypted = None
        case.patient_code_lookup = None
        return
    cipher = get_patient_data_cipher()
    case.patient_code_encrypted = cipher.encrypt(
        value,
        case_id=case.id,
        field="patient_code",
    )
    case.patient_code_lookup = cipher.lookup_digest(value)


def get_patient_code(case: DentalCase) -> str | None:
    if case.patient_code_encrypted is None:
        return None
    return get_patient_data_cipher().decrypt(
        case.patient_code_encrypted,
        case_id=case.id,
        field="patient_code",
    )


def set_patient_name(case: DentalCase, value: str | None) -> None:
    _ensure_case_id(case)
    case.patient_name_encrypted = (
        get_patient_data_cipher().encrypt(value, case_id=case.id, field="patient_name")
        if value is not None
        else None
    )


def set_patient_identity(
    case: DentalCase,
    *,
    patient_code: str | None,
    patient_name: str | None = None,
) -> None:
    set_patient_code(case, patient_code)
    set_patient_name(case, patient_name)


def get_patient_name(case: DentalCase) -> str | None:
    if case.patient_name_encrypted is None:
        return None
    return get_patient_data_cipher().decrypt(
        case.patient_name_encrypted,
        case_id=case.id,
        field="patient_name",
    )


def patient_code_lookup(value: str) -> bytes:
    return get_patient_data_cipher().lookup_digest(value)


def protected_value_state(value: object) -> dict[str, bool]:
    return {"is_set": value is not None}


def _ensure_case_id(case: DentalCase) -> None:
    if case.id is None:
        case.id = uuid4()
