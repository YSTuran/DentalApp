from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.models import CaseStatus


class ReportTotalsResponse(BaseModel):
    total: int
    active: int
    completed: int
    closed: int
    returned: int
    reproductions: int
    overdue: int
    average_completion_hours: float | None


class ReportCountResponse(BaseModel):
    key: str
    label: str
    count: int


class ReportClinicResponse(BaseModel):
    id: UUID
    name: str
    count: int = 0


class ReportDentistResponse(BaseModel):
    id: UUID
    full_name: str
    count: int


class ReportStageDurationResponse(BaseModel):
    status: CaseStatus
    average_hours: float
    sample_size: int


class CaseReportResponse(BaseModel):
    date_from: date | None
    date_to: date | None
    clinic_id: UUID | None
    generated_at: datetime
    totals: ReportTotalsResponse
    status_counts: list[ReportCountResponse]
    clinic_counts: list[ReportClinicResponse]
    dentist_counts: list[ReportDentistResponse]
    stage_durations: list[ReportStageDurationResponse]
    available_clinics: list[ReportClinicResponse]
