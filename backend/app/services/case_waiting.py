from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import CaseStatus, CaseStatusHistory, CaseWaitAlert, DentalCase, RoleCode
from app.services.case_notifications import user_ids_with_roles
from app.services.notification_delivery import add_user_notification

STATUS_LABELS = {
    CaseStatus.MANAGER_REVIEW: "yönetici onayı",
    CaseStatus.MANAGER_REVISION_REQUESTED: "tarama düzeltmesi",
    CaseStatus.LAB_DESIGN: "laboratuvar tasarımı",
    CaseStatus.DENTIST_REVIEW: "hekim tasarım onayı",
    CaseStatus.DESIGN_REVISION_REQUESTED: "tasarım düzeltmesi",
    CaseStatus.READY_FOR_PRODUCTION: "üretim sırası",
    CaseStatus.IN_PRODUCTION: "üretim",
    CaseStatus.PRODUCTION_COMPLETED: "kargoya hazırlık",
    CaseStatus.SHIPPED: "şube teslimi",
    CaseStatus.RETURN_REVIEW: "iade kararı",
    CaseStatus.REPRODUCTION_REQUESTED: "yeniden üretim sırası",
    CaseStatus.RESCAN_REQUESTED: "yeni tarama",
}

MANAGER_STATUSES = {CaseStatus.MANAGER_REVIEW, CaseStatus.RETURN_REVIEW}
TECHNICIAN_STATUSES = {
    CaseStatus.LAB_DESIGN,
    CaseStatus.DESIGN_REVISION_REQUESTED,
    CaseStatus.READY_FOR_PRODUCTION,
    CaseStatus.IN_PRODUCTION,
    CaseStatus.PRODUCTION_COMPLETED,
    CaseStatus.REPRODUCTION_REQUESTED,
}
STAKEHOLDER_STATUSES = {
    CaseStatus.MANAGER_REVISION_REQUESTED,
    CaseStatus.RESCAN_REQUESTED,
}
CASE_WAIT_ALERT_LOCK_NAMESPACE = 4_474_450
CASE_WAIT_ALERT_LOCK_KEY = 1


def _recipient_ids(db: Session, case: DentalCase) -> set[UUID]:
    if case.status in MANAGER_STATUSES:
        return user_ids_with_roles(
            db, [RoleCode.MANAGING_DENTIST], clinic_id=case.clinic_id
        )
    if case.status in TECHNICIAN_STATUSES:
        return user_ids_with_roles(db, [RoleCode.TECHNICIAN])
    if case.status == CaseStatus.DENTIST_REVIEW:
        return {case.responsible_dentist_user_id}
    if case.status == CaseStatus.SHIPPED:
        return user_ids_with_roles(
            db,
            [RoleCode.CLINIC_MANAGER, RoleCode.CLINIC_STAFF],
            clinic_id=case.clinic_id,
        ) | {case.responsible_dentist_user_id}
    if case.status in STAKEHOLDER_STATUSES:
        return {case.created_by_user_id, case.responsible_dentist_user_id}
    return set()


def create_overdue_case_alerts(db: Session, *, limit: int = 200) -> int:
    lock_acquired = db.scalar(
        select(
            func.pg_try_advisory_xact_lock(
                CASE_WAIT_ALERT_LOCK_NAMESPACE,
                CASE_WAIT_ALERT_LOCK_KEY,
            )
        )
    )
    if not lock_acquired:
        return 0

    configured = get_settings().case_wait_warning_hours
    policies = {
        CaseStatus(status): hours
        for status, hours in configured.items()
        if status in CaseStatus._value2member_map_
    }
    cases = db.scalars(
        select(DentalCase)
        .where(DentalCase.status.in_(policies))
        .order_by(DentalCase.updated_at)
        .limit(limit)
    ).all()
    now = datetime.now(UTC)
    created = 0

    for case in cases:
        history = db.scalar(
            select(CaseStatusHistory)
            .where(CaseStatusHistory.case_id == case.id)
            .order_by(CaseStatusHistory.sequence_number.desc())
            .limit(1)
        )
        if history is None or history.to_status != case.status:
            continue
        threshold = policies[case.status]
        if history.created_at + timedelta(hours=threshold) > now:
            continue

        for recipient_id in _recipient_ids(db, case):
            exists = db.scalar(
                select(CaseWaitAlert.id).where(
                    CaseWaitAlert.case_id == case.id,
                    CaseWaitAlert.case_status == case.status,
                    CaseWaitAlert.recipient_user_id == recipient_id,
                    CaseWaitAlert.stage_started_at == history.created_at,
                )
            )
            if exists is not None:
                continue
            label = STATUS_LABELS[case.status]
            notification = add_user_notification(
                db,
                recipient_user_id=recipient_id,
                actor_user_id=None,
                case_id=case.id,
                kind="case.waiting_warning",
                title="Bekleme süresi aşıldı",
                message=(
                    f"{case.case_number}, {label} aşamasında "
                    f"{threshold} saatten uzun süredir bekliyor."
                ),
                target_path=f"/vakalar/{case.id}",
            )
            if notification is None:
                continue
            db.add(
                CaseWaitAlert(
                    case_id=case.id,
                    case_status=case.status,
                    recipient_user_id=recipient_id,
                    notification_id=notification.id,
                    stage_started_at=history.created_at,
                    threshold_hours=threshold,
                    created_at=now,
                )
            )
            created += 1
    db.commit()
    return created
