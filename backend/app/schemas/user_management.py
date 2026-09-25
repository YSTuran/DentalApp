import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import RoleCode

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} boş bırakılamaz.")
    return normalized


def _optional_reason(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=1, max_length=200)
    role: RoleCode
    clinic_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = _required_text(value, "E-posta").lower()
        if EMAIL_PATTERN.fullmatch(normalized) is None:
            raise ValueError("Geçerli bir e-posta adresi girilmelidir.")
        return normalized

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return _required_text(value, "Ad soyad")

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        return _optional_reason(value)


class UserUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return _required_text(value, "Ad soyad")

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        return _optional_reason(value)


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        return _required_text(value, "Gerekçe")


class RoleAssignmentCreateRequest(BaseModel):
    role: RoleCode
    clinic_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        return _optional_reason(value)


class RoleAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: RoleCode
    clinic_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ManagedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    role_assignments: list[RoleAssignmentResponse]


class ManagedUserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    total: int
    limit: int
    offset: int


class UserCreatedResponse(BaseModel):
    user: ManagedUserResponse
    temporary_password: str
