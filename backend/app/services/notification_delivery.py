from datetime import UTC, datetime
from html import escape
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import EmailOutbox, Notification, User


def _email_bodies(title: str, message: str, target_path: str | None) -> tuple[str, str]:
    settings = get_settings()
    target_url = (
        f"{settings.frontend_base_url.rstrip('/')}{target_path}"
        if target_path is not None
        else None
    )
    text_lines = ["DentalApp", "", title, message]
    if target_url:
        text_lines.extend(["", f"Vakayı görüntüle: {target_url}"])
    text_lines.extend(["", "DEMO — Bu e-posta gerçek hasta bilgisi içermez."])

    link = (
        f'<p><a href="{escape(target_url, quote=True)}" '
        'style="display:inline-block;padding:10px 16px;border-radius:8px;'
        'background:#087c8c;color:#fff;text-decoration:none;font-weight:700">'
        "Vakayı görüntüle</a></p>"
        if target_url
        else ""
    )
    html = (
        '<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;'
        'color:#163b3f"><h1 style="font-size:20px">DentalApp</h1>'
        f"<h2>{escape(title)}</h2><p>{escape(message)}</p>{link}"
        '<p style="color:#697b7e;font-size:12px">'
        "DEMO — Bu e-posta gerçek hasta bilgisi içermez.</p></div>"
    )
    return "\n".join(text_lines), html


def add_user_notification(
    db: Session,
    *,
    recipient_user_id: UUID,
    actor_user_id: UUID | None,
    case_id: UUID | None,
    kind: str,
    title: str,
    message: str,
    target_path: str | None,
) -> Notification | None:
    recipient = db.get(User, recipient_user_id)
    if recipient is None or not recipient.is_active:
        return None

    notification = Notification(
        recipient_user_id=recipient.id,
        actor_user_id=actor_user_id,
        case_id=case_id,
        kind=kind,
        title=title,
        message=message,
        target_path=target_path,
    )
    db.add(notification)
    db.flush()

    if get_settings().email_enabled:
        body_text, body_html = _email_bodies(title, message, target_path)
        db.add(
            EmailOutbox(
                notification_id=notification.id,
                recipient_user_id=recipient.id,
                recipient_email=recipient.email,
                subject=f"DentalApp · {title}",
                body_text=body_text,
                body_html=body_html,
                next_attempt_at=datetime.now(UTC),
            )
        )
    return notification
