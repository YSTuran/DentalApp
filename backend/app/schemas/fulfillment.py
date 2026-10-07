from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import ReturnReasonCode, ReturnResolution


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _required_text(value: str) -> str:
    normalized = value.strip()
    if len(normalized) < 3:
        raise ValueError("Açıklama en az 3 karakter olmalıdır.")
    return normalized


class ProductionStartRequest(BaseModel):
    design_file_version_id: UUID
    notes: str | None = Field(default=None, max_length=2000)

    _normalize_notes = field_validator("notes")(_optional_text)


class ProductionCompleteRequest(BaseModel):
    production_run_id: UUID
    material: str = Field(min_length=1, max_length=200)
    lot_number: str = Field(min_length=1, max_length=120)
    quantity: int = Field(default=1, gt=0, le=10_000)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("material", "lot_number")
    @classmethod
    def normalize_required_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Bu alan boş bırakılamaz.")
        return normalized

    _normalize_notes = field_validator("notes")(_optional_text)


class ShipmentCreateRequest(BaseModel):
    production_run_id: UUID
    carrier: str = Field(min_length=1, max_length=120)
    tracking_number: str = Field(min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("carrier", "tracking_number")
    @classmethod
    def normalize_required_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Bu alan boş bırakılamaz.")
        return normalized

    _normalize_notes = field_validator("notes")(_optional_text)


class DeliveryConfirmRequest(BaseModel):
    shipment_id: UUID
    notes: str | None = Field(default=None, max_length=2000)

    _normalize_notes = field_validator("notes")(_optional_text)


class ReturnReceiptCreateRequest(BaseModel):
    shipment_id: UUID
    reason_code: ReturnReasonCode
    reason: str = Field(min_length=3, max_length=2000)
    inspection_notes: str | None = Field(default=None, max_length=2000)

    _normalize_reason = field_validator("reason")(_required_text)
    _normalize_inspection_notes = field_validator("inspection_notes")(_optional_text)


class ReturnDecisionRequest(BaseModel):
    return_receipt_id: UUID
    resolution: ReturnResolution
    reason: str = Field(min_length=3, max_length=2000)

    _normalize_reason = field_validator("reason")(_required_text)


class ProductionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    attempt_number: int
    design_file_version_id: UUID
    work_order_number: str
    started_by_user_id: UUID
    notes: str | None
    started_at: datetime


class ProductionCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_run_id: UUID
    material: str
    lot_number: str
    quantity: int
    completed_by_user_id: UUID
    notes: str | None
    completed_at: datetime


class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_run_id: UUID
    destination_clinic_id: UUID
    carrier: str
    tracking_number: str
    shipped_by_user_id: UUID
    notes: str | None
    shipped_at: datetime


class DeliveryConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shipment_id: UUID
    received_by_user_id: UUID
    notes: str | None
    delivered_at: datetime


class ReturnReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shipment_id: UUID
    reason_code: ReturnReasonCode
    reason: str
    inspection_notes: str | None
    received_by_user_id: UUID
    received_at: datetime


class ReturnDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    return_receipt_id: UUID
    source_scan_file_version_id: UUID
    reproduction_case_id: UUID | None
    resolution: ReturnResolution
    reason: str
    decided_by_user_id: UUID
    decided_at: datetime


class CaseOperationsResponse(BaseModel):
    production_runs: list[ProductionRunResponse]
    production_completions: list[ProductionCompletionResponse]
    shipments: list[ShipmentResponse]
    delivery_confirmations: list[DeliveryConfirmationResponse]
    return_receipts: list[ReturnReceiptResponse]
    return_decisions: list[ReturnDecisionResponse]
