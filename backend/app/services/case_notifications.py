from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DentalCase, RoleCode, User, UserClinicAssignment, UserRoleAssignment
from app.services.notification_delivery import add_user_notification

MANAGER_ACTIONS = {"case.submitted", "case.return_received"}
TECHNICIAN_ACTIONS = {
    "case.manager_approved",
    "case.design_approved",
    "case.design_revision_requested",
    "case.delivery_confirmed",
}
STAKEHOLDER_ACTIONS = {
    "case.manager_revision_requested",
    "case.manager_rejected",
    "case.rescan_requested",
    "case.reproduction_requested",
    "case.cancelled",
}

NOTIFICATION_CONTENT = {
    "case.submitted": ("Yönetici onayı bekleniyor", "{case} incelemenize gönderildi."),
    "case.manager_approved": ("Yeni laboratuvar işi", "{case} tasarım için hazır."),
    "case.manager_revision_requested": (
        "Tarama düzeltmesi istendi",
        "{case} için yeni tarama gerekiyor.",
    ),
    "case.manager_rejected": ("Vaka reddedildi", "{case} kesin olarak reddedildi."),
    "case.design_submitted": ("Tasarım onayı bekleniyor", "{case} tasarım onayınıza gönderildi."),
    "case.design_approved": ("Üretim onayı tamamlandı", "{case} üretime hazır."),
    "case.design_revision_requested": (
        "Tasarım düzeltmesi istendi",
        "{case} için yeni tasarım gerekiyor.",
    ),
    "case.shipped": ("Ürün kargoya verildi", "{case} kliniğe gönderildi."),
    "case.delivery_confirmed": ("Teslimat doğrulandı", "{case} klinik tarafından teslim alındı."),
    "case.return_received": ("İade kararı bekleniyor", "{case} iadesi laboratuvara ulaştı."),
    "case.reproduction_requested": (
        "Yeniden üretim vakası açıldı",
        "{case} için bağlantılı yeni bir yeniden üretim vakası açıldı.",
    ),
    "case.rescan_requested": ("Yeni tarama istendi", "{case} için yeni ağız içi tarama gerekiyor."),
    "case.cancelled": ("Vaka iptal edildi", "{case} iptal edildi."),
}


def user_ids_with_roles(
    db: Session,
    roles: Iterable[RoleCode],
    *,
    clinic_id: UUID | None = None,
) -> set[UUID]:
    conditions = [
        User.is_active.is_(True),
        UserRoleAssignment.is_active.is_(True),
        UserRoleAssignment.role.in_(set(roles)),
    ]
    if clinic_id is not None:
        conditions.extend(
            [
                UserClinicAssignment.clinic_id == clinic_id,
                UserClinicAssignment.is_active.is_(True),
            ]
        )
    statement = select(User.id).join(
        UserRoleAssignment,
        UserRoleAssignment.user_id == User.id,
    )
    if clinic_id is not None:
        statement = statement.join(
            UserClinicAssignment,
            UserClinicAssignment.user_id == User.id,
        )
    return set(
        db.scalars(
            statement.where(*conditions).distinct()
        )
    )


def _recipients_for_action(db: Session, case: DentalCase, action: str) -> set[UUID]:
    if action in MANAGER_ACTIONS:
        return user_ids_with_roles(
            db,
            [RoleCode.MANAGING_DENTIST],
            clinic_id=case.clinic_id,
        )
    if action in TECHNICIAN_ACTIONS:
        return user_ids_with_roles(db, [RoleCode.TECHNICIAN])
    if action == "case.design_submitted":
        return {case.responsible_dentist_user_id}
    if action == "case.shipped":
        return user_ids_with_roles(
            db,
            [RoleCode.CLINIC_MANAGER, RoleCode.CLINIC_STAFF],
            clinic_id=case.clinic_id,
        ) | {case.responsible_dentist_user_id}
    if action in STAKEHOLDER_ACTIONS:
        return {case.created_by_user_id, case.responsible_dentist_user_id}
    return set()


def create_case_notifications(
    db: Session,
    *,
    case: DentalCase,
    action: str,
    actor: User,
) -> None:
    content = NOTIFICATION_CONTENT.get(action)
    if content is None:
        return
    recipients = _recipients_for_action(db, case, action)
    recipients.discard(actor.id)
    title, message = content
    for recipient_id in recipients:
        add_user_notification(
            db,
            recipient_user_id=recipient_id,
            actor_user_id=actor.id,
            case_id=case.id,
            kind=action,
            title=title,
            message=message.format(case=case.case_number),
            target_path=f"/vakalar/{case.id}",
        )
