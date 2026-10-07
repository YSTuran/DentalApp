from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import CaseTransferStatus


def _required_reason(value: str) -> str:
    normalized = value.strip()
    if len(normalized) < 3:
        raise ValueError("Gerekçe en az 3 karakter olmalıdır.")
    return normalized


class CaseTransferCreateRequest(BaseModel):
    to_dentist_user_id: UUID
    reason: str = Field(min_length=3, max_length=2000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        return _required_reason(value)


class CaseTransferDecisionRequest(BaseModel):
    decision: CaseTransferStatus
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: CaseTransferStatus) -> CaseTransferStatus:
        if value == CaseTransferStatus.PENDING:
            raise ValueError("Beklemede kararı gönderilemez.")
        return value

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "CaseTransferDecisionRequest":
        if self.decision == CaseTransferStatus.REJECTED and len(self.reason or "") < 3:
            raise ValueError("Ret gerekçesi en az 3 karakter olmalıdır.")
        return self


class CaseTransferOptionResponse(BaseModel):
    id: UUID
    full_name: str


class CaseTransferOptionsResponse(BaseModel):
    items: list[CaseTransferOptionResponse]


class CaseTransferResponse(BaseModel):
    id: UUID
    case_id: UUID
    from_dentist_user_id: UUID
    from_dentist_name: str
    to_dentist_user_id: UUID
    to_dentist_name: str
    requested_by_user_id: UUID
    requested_by_name: str
    decided_by_user_id: UUID | None
    decided_by_name: str | None
    status: CaseTransferStatus
    request_reason: str
    decision_reason: str | None
    requested_at: datetime
    decided_at: datetime | None


class CaseTransferListResponse(BaseModel):
    items: list[CaseTransferResponse]
