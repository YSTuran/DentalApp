import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CLINIC_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
CLINIC_UPDATE_FIELDS = {"code", "name", "address", "phone"}


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} boş bırakılamaz.")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _clinic_code(value: str) -> str:
    normalized = _required_text(value, "Klinik kodu").upper()
    if CLINIC_CODE_PATTERN.fullmatch(normalized) is None:
        raise ValueError("Klinik kodu yalnızca A-Z, 0-9, kısa çizgi ve alt çizgi içerebilir.")
    return normalized


class ClinicCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=32)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        return _clinic_code(value)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _required_text(value, "Klinik adı")

    @field_validator("address", "phone", "reason")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value)


class ClinicUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = None
    phone: str | None = Field(default=None, max_length=32)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        return _clinic_code(value) if value is not None else None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return _required_text(value, "Klinik adı") if value is not None else None

    @field_validator("address", "phone", "reason")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @model_validator(mode="after")
    def require_update_field(self) -> "ClinicUpdateRequest":
        provided_fields = self.model_fields_set & CLINIC_UPDATE_FIELDS
        if not provided_fields:
            raise ValueError("Güncellenecek en az bir klinik alanı gönderilmelidir.")
        if "code" in provided_fields and self.code is None:
            raise ValueError("Klinik kodu null olamaz.")
        if "name" in provided_fields and self.name is None:
            raise ValueError("Klinik adı null olamaz.")
        return self


class ClinicStatusChangeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        return _required_text(value, "Gerekçe")


class ClinicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    address: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClinicListResponse(BaseModel):
    items: list[ClinicResponse]
    total: int
    limit: int
    offset: int
