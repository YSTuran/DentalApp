import pytest
from pydantic import ValidationError

from app.schemas.clinic import (
    ClinicCreateRequest,
    ClinicStatusChangeRequest,
    ClinicUpdateRequest,
)


def test_clinic_create_normalizes_code_and_text() -> None:
    payload = ClinicCreateRequest(
        code=" ist-001 ",
        name="  DentalApp İstanbul  ",
        address="   ",
        phone=" +90 212 000 00 00 ",
    )

    assert payload.code == "IST-001"
    assert payload.name == "DentalApp İstanbul"
    assert payload.address is None
    assert payload.phone == "+90 212 000 00 00"


@pytest.mark.parametrize("code", ["şube 1", "clinic/1", "-clinic"])
def test_clinic_create_rejects_invalid_code(code: str) -> None:
    with pytest.raises(ValidationError):
        ClinicCreateRequest(code=code, name="Test Clinic")


def test_clinic_update_requires_at_least_one_business_field() -> None:
    with pytest.raises(ValidationError, match="Güncellenecek en az bir"):
        ClinicUpdateRequest(reason="Yalnızca gerekçe")


def test_clinic_update_allows_clearing_optional_fields() -> None:
    payload = ClinicUpdateRequest(address=None)

    assert payload.model_fields_set == {"address"}
    assert payload.address is None


def test_status_change_requires_non_blank_reason() -> None:
    with pytest.raises(ValidationError):
        ClinicStatusChangeRequest(reason="   ")
