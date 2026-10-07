from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models import (
    CaseStatus,
    CaseStatusHistory,
    Clinic,
    DentalCase,
    ProductionRun,
    ReturnReceipt,
    RoleCode,
    Shipment,
    User,
)
from app.schemas.report import (
    CaseReportResponse,
    ReportClinicResponse,
    ReportCountResponse,
    ReportDentistResponse,
    ReportStageDurationResponse,
    ReportTotalsResponse,
)
from app.services.authorization import has_global_role
from app.services.case_management.access import case_visibility_filter
from app.services.case_management.exceptions import CaseAccessDeniedError, CaseValidationError
from app.services.case_management.queries import TERMINAL_CASE_STATUSES

STATUS_LABELS = {
    CaseStatus.DRAFT: "Taslak",
    CaseStatus.MANAGER_REVIEW: "Yönetici onayı",
    CaseStatus.MANAGER_REVISION_REQUESTED: "Tarama düzeltmesi",
    CaseStatus.MANAGER_REJECTED: "Kesin ret",
    CaseStatus.LAB_DESIGN: "Laboratuvar tasarımı",
    CaseStatus.DENTIST_REVIEW: "Hekim tasarım onayı",
    CaseStatus.DESIGN_REVISION_REQUESTED: "Tasarım düzeltmesi",
    CaseStatus.READY_FOR_PRODUCTION: "Üretime hazır",
    CaseStatus.IN_PRODUCTION: "Üretimde",
    CaseStatus.PRODUCTION_COMPLETED: "Üretildi",
    CaseStatus.SHIPPED: "Kargoya verildi",
    CaseStatus.DELIVERED: "Şubeye teslim edildi",
    CaseStatus.RETURN_REVIEW: "İade değerlendirmesi",
    CaseStatus.REPRODUCTION_REQUESTED: "Yeniden üretim",
    CaseStatus.RESCAN_REQUESTED: "Yeni tarama",
    CaseStatus.CANCELLED: "İptal edildi",
}


def _has_global_report_scope(actor: User) -> bool:
    return has_global_role(actor, RoleCode.SYSTEM_ADMIN, RoleCode.TECHNICIAN)


def _available_clinics(db: Session, actor: User) -> list[Clinic]:
    statement = select(Clinic)
    if not _has_global_report_scope(actor):
        clinic_ids = {
            assignment.clinic_id
            for assignment in actor.clinic_assignments
            if assignment.is_active
        }
        statement = statement.where(Clinic.id.in_(clinic_ids))
    return list(db.scalars(statement.order_by(Clinic.name, Clinic.id)).all())


def _date_bounds(
    date_from: date | None,
    date_to: date | None,
) -> tuple[datetime | None, datetime | None]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise CaseValidationError("report_date_range_invalid")
    start = datetime.combine(date_from, time.min, tzinfo=UTC) if date_from else None
    end = (
        datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        if date_to
        else None
    )
    return start, end


def _stage_metrics(
    histories: list[CaseStatusHistory],
) -> tuple[list[ReportStageDurationResponse], dict[UUID, list[CaseStatusHistory]]]:
    by_case: dict[UUID, list[CaseStatusHistory]] = defaultdict(list)
    for history in histories:
        by_case[history.case_id].append(history)

    durations: dict[CaseStatus, list[float]] = defaultdict(list)
    for items in by_case.values():
        for current, following in zip(items, items[1:], strict=False):
            hours = (following.created_at - current.created_at).total_seconds() / 3600
            if hours >= 0:
                durations[current.to_status].append(hours)
    response = [
        ReportStageDurationResponse(
            status=status,
            average_hours=round(sum(values) / len(values), 1),
            sample_size=len(values),
        )
        for status, values in durations.items()
    ]
    response.sort(key=lambda item: list(CaseStatus).index(item.status))
    return response, by_case


def _overdue_count(
    cases: list[DentalCase],
    histories: dict[UUID, list[CaseStatusHistory]],
    now: datetime,
) -> int:
    policies = {
        CaseStatus(status): hours
        for status, hours in get_settings().case_wait_warning_hours.items()
        if status in CaseStatus._value2member_map_
    }
    count = 0
    for case in cases:
        items = histories.get(case.id, [])
        if case.status not in policies or not items:
            continue
        latest = items[-1]
        if latest.to_status == case.status and latest.created_at + timedelta(
            hours=policies[case.status]
        ) <= now:
            count += 1
    return count


def generate_case_report(
    db: Session,
    *,
    actor: User,
    date_from: date | None,
    date_to: date | None,
    clinic_id: UUID | None,
) -> CaseReportResponse:
    start, end = _date_bounds(date_from, date_to)
    available_clinics = _available_clinics(db, actor)
    available_ids = {clinic.id for clinic in available_clinics}
    if clinic_id is not None and clinic_id not in available_ids:
        raise CaseAccessDeniedError

    filters = []
    visibility = case_visibility_filter(actor)
    if visibility is not None:
        filters.append(visibility)
    if start is not None:
        filters.append(DentalCase.created_at >= start)
    if end is not None:
        filters.append(DentalCase.created_at < end)
    if clinic_id is not None:
        filters.append(DentalCase.clinic_id == clinic_id)

    cases = list(
        db.scalars(
            select(DentalCase)
            .where(*filters)
            .options(
                selectinload(DentalCase.clinic),
                selectinload(DentalCase.responsible_dentist),
            )
            .order_by(DentalCase.created_at)
        ).all()
    )
    case_ids = [case.id for case in cases]
    histories = (
        list(
            db.scalars(
                select(CaseStatusHistory)
                .where(CaseStatusHistory.case_id.in_(case_ids))
                .order_by(CaseStatusHistory.case_id, CaseStatusHistory.sequence_number)
            ).all()
        )
        if case_ids
        else []
    )
    stage_durations, histories_by_case = _stage_metrics(histories)

    returned = 0
    if case_ids:
        returned = int(
            db.scalar(
                select(func.count(func.distinct(ProductionRun.case_id)))
                .select_from(ReturnReceipt)
                .join(Shipment, Shipment.id == ReturnReceipt.shipment_id)
                .join(ProductionRun, ProductionRun.id == Shipment.production_run_id)
                .where(ProductionRun.case_id.in_(case_ids))
            )
            or 0
        )
    reproduction_ids = {
        history.case_id
        for history in histories
        if history.to_status == CaseStatus.REPRODUCTION_REQUESTED
    }

    status_counts: dict[CaseStatus, int] = defaultdict(int)
    clinic_counts: dict[UUID, int] = defaultdict(int)
    dentist_counts: dict[UUID, int] = defaultdict(int)
    dentists: dict[UUID, str] = {}
    completion_hours: list[float] = []
    for case in cases:
        status_counts[case.status] += 1
        clinic_counts[case.clinic_id] += 1
        dentist_counts[case.responsible_dentist_user_id] += 1
        dentists[case.responsible_dentist_user_id] = case.responsible_dentist.full_name
        delivered = next(
            (
                item
                for item in histories_by_case.get(case.id, [])
                if item.to_status == CaseStatus.DELIVERED
            ),
            None,
        )
        if delivered is not None:
            completion_hours.append((delivered.created_at - case.created_at).total_seconds() / 3600)

    total = len(cases)
    completed = status_counts[CaseStatus.DELIVERED]
    closed = status_counts[CaseStatus.CANCELLED] + status_counts[CaseStatus.MANAGER_REJECTED]
    now = datetime.now(UTC)
    clinic_names = {clinic.id: clinic.name for clinic in available_clinics}
    return CaseReportResponse(
        date_from=date_from,
        date_to=date_to,
        clinic_id=clinic_id,
        generated_at=now,
        totals=ReportTotalsResponse(
            total=total,
            active=sum(1 for case in cases if case.status not in TERMINAL_CASE_STATUSES),
            completed=completed,
            closed=closed,
            returned=returned,
            reproductions=len(reproduction_ids),
            overdue=_overdue_count(cases, histories_by_case, now),
            average_completion_hours=(
                round(sum(completion_hours) / len(completion_hours), 1)
                if completion_hours
                else None
            ),
        ),
        status_counts=[
            ReportCountResponse(key=status.value, label=STATUS_LABELS[status], count=count)
            for status in CaseStatus
            if (count := status_counts[status]) > 0
        ],
        clinic_counts=[
            ReportClinicResponse(
                id=current_clinic_id,
                name=clinic_names.get(current_clinic_id, "Klinik"),
                count=count,
            )
            for current_clinic_id, count in sorted(
                clinic_counts.items(), key=lambda item: clinic_names.get(item[0], "")
            )
        ],
        dentist_counts=[
            ReportDentistResponse(id=dentist_id, full_name=dentists[dentist_id], count=count)
            for dentist_id, count in sorted(
                dentist_counts.items(), key=lambda item: (-item[1], dentists[item[0]])
            )
        ],
        stage_durations=stage_durations,
        available_clinics=[
            ReportClinicResponse(id=clinic.id, name=clinic.name, count=clinic_counts[clinic.id])
            for clinic in available_clinics
        ],
    )
