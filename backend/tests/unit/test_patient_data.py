from uuid import uuid4

import pytest

from app.core.patient_data import PatientDataCipher, PatientDataIntegrityError


@pytest.fixture
def cipher() -> PatientDataCipher:
    return PatientDataCipher(
        keys={"v1": b"a" * 32},
        active_key_id="v1",
        lookup_key=b"b" * 32,
    )


def test_patient_data_round_trip_uses_randomized_authenticated_encryption(
    cipher: PatientDataCipher,
) -> None:
    case_id = uuid4()
    first = cipher.encrypt("Demo Hasta", case_id=case_id, field="patient_name")
    second = cipher.encrypt("Demo Hasta", case_id=case_id, field="patient_name")

    assert first != second
    assert b"Demo Hasta" not in first
    assert cipher.decrypt(first, case_id=case_id, field="patient_name") == "Demo Hasta"


def test_patient_data_rejects_tampering_or_wrong_context(cipher: PatientDataCipher) -> None:
    case_id = uuid4()
    encrypted = cipher.encrypt("HST-001", case_id=case_id, field="patient_code")
    tampered = encrypted[:-1] + bytes([encrypted[-1] ^ 1])

    with pytest.raises(PatientDataIntegrityError):
        cipher.decrypt(tampered, case_id=case_id, field="patient_code")
    with pytest.raises(PatientDataIntegrityError):
        cipher.decrypt(encrypted, case_id=uuid4(), field="patient_code")
    with pytest.raises(PatientDataIntegrityError):
        cipher.decrypt(encrypted, case_id=case_id, field="patient_name")
    with pytest.raises(PatientDataIntegrityError):
        cipher.decrypt(b"DP1", case_id=case_id, field="patient_code")


def test_patient_code_lookup_is_exact_but_case_insensitive(cipher: PatientDataCipher) -> None:
    assert cipher.lookup_digest(" HST-İ01 ") == cipher.lookup_digest("hst-i̇01")
    assert cipher.lookup_digest("HST-İ01") != cipher.lookup_digest("HST-İ0")
