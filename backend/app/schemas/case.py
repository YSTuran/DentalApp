import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import CaseFileKind, CaseStatus, MeshValidationStatus

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


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_tooth_numbers(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        tooth = value.strip()
        if not tooth:
            raise ValueError("Diş numarası boş bırakılamaz.")
        if not (
            len(tooth) == 2
            and tooth.isdigit()
            and (
                (tooth[0] in "1234" and tooth[1] in "12345678")
                or (tooth[0] in "5678" and tooth[1] in "12345")
            )
        ):
            raise ValueError(f"'{tooth}' geçerli bir FDI diş numarası değildir.")
        if tooth not in normalized:
            normalized.append(tooth)
    return normalized


def _validate_extra_fields(value: dict[str, Any]) -> dict[str, Any]:
    if len(value) > 50:
        raise ValueError("En fazla 50 dinamik alan gönderilebilir.")
    if any(not str(key).strip() for key in value):
        raise ValueError("Dinamik alan adları boş bırakılamaz.")
    if len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")) > 16_384:
        raise ValueError("Dinamik alanların toplam boyutu 16 KB'ı aşamaz.")
    return value


class CaseCreateRequest(BaseModel):
    clinic_id: UUID
    responsible_dentist_user_id: UUID
    patient_code: str | None = Field(default=None, max_length=100)
    patient_name: str | None = Field(default=None, max_length=200)
    appliance_type: str | None = Field(default=None, max_length=100)
    material: str | None = Field(default=None, max_length=100)
    tooth_numbers: list[str] = Field(default_factory=list, max_length=52)
    special_notes: str | None = Field(default=None, max_length=5000)
    extra_fields: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "patient_code",
        "patient_name",
        "appliance_type",
        "material",
        "special_notes",
        "reason",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @field_validator("tooth_numbers")
    @classmethod
    def validate_tooth_numbers(cls, value: list[str]) -> list[str]:
        return _normalize_tooth_numbers(value)

    @field_validator("extra_fields")
    @classmethod
    def validate_extra_fields(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_extra_fields(value)


class CaseUpdateRequest(BaseModel):
    responsible_dentist_user_id: UUID | None = None
    patient_code: str | None = Field(default=None, max_length=100)
    patient_name: str | None = Field(default=None, max_length=200)
    appliance_type: str | None = Field(default=None, max_length=100)
    material: str | None = Field(default=None, max_length=100)
    tooth_numbers: list[str] | None = Field(default=None, max_length=52)
    special_notes: str | None = Field(default=None, max_length=5000)
    extra_fields: dict[str, Any] | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "patient_code",
        "patient_name",
        "appliance_type",
        "material",
        "special_notes",
        "reason",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @field_validator("tooth_numbers")
    @classmethod
    def validate_tooth_numbers(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_tooth_numbers(value) if value is not None else None

    @field_validator("extra_fields")
    @classmethod
    def validate_extra_fields(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return _validate_extra_fields(value) if value is not None else None

    @model_validator(mode="after")
    def require_update_field(self) -> "CaseUpdateRequest":
        provided_fields = self.model_fields_set & CASE_UPDATE_FIELDS
        if not provided_fields:
            raise ValueError("Güncellenecek en az bir vaka alanı gönderilmelidir.")
        if (
            "responsible_dentist_user_id" in provided_fields
            and self.responsible_dentist_user_id is None
        ):
            raise ValueError("Sorumlu hekim null olamaz.")
        if "tooth_numbers" in provided_fields and self.tooth_numbers is None:
            raise ValueError("Diş numaraları null olamaz; temizlemek için boş liste gönderin.")
        if "extra_fields" in provided_fields and self.extra_fields is None:
            raise ValueError("Dinamik alanlar null olamaz; temizlemek için boş nesne gönderin.")
        return self


class CaseCancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Gerekçe en az 3 karakter olmalıdır.")
        return normalized


class CaseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    appliance_type: str | None
    material: str | None
    tooth_numbers: list[str]
    special_notes: str | None
    extra_fields: dict[str, Any]


class CaseFileVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: CaseFileKind
    version_number: int
    original_filename: str | None = None
    size_bytes: int
    mesh_status: MeshValidationStatus
    is_locked: bool
    uploaded_by_user_id: UUID
    created_at: datetime


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_number: str
    clinic_id: UUID
    created_by_user_id: UUID
    responsible_dentist_user_id: UUID
    patient_code: str | None
    patient_name: str | None = None
    status: CaseStatus
    submitted_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    details: CaseDetailResponse
    file_versions: list[CaseFileVersionResponse]


class CaseListResponse(BaseModel):
    items: list[CaseResponse]
    total: int
    limit: int
    offset: int


class CaseStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_status: CaseStatus | None
    to_status: CaseStatus
    action: str
    actor_user_id: UUID
    reason: str | None
    created_at: datetime


class CaseHistoryListResponse(BaseModel):
    items: list[CaseStatusHistoryResponse]
