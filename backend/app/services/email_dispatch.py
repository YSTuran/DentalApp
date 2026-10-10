import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import EmailOutbox

PROCESSING_TIMEOUT_MINUTES = 10
MAX_RETRY_SECONDS = 3600


def _build_email(item: EmailOutbox, settings: Settings) -> EmailMessage:
    message = EmailMessage()
    message["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
    message["To"] = item.recipient_email
    message["Subject"] = item.subject
    message_id_domain = settings.email_from_address.rsplit("@", 1)[-1] or "dentflow.local"
    message["Message-ID"] = f"<outbox-{item.id}@{message_id_domain}>"
    message["X-DentFlow-Outbox-ID"] = str(item.id)
    message.set_content(item.body_text)
    message.add_alternative(item.body_html, subtype="html")
    return message


def _send_email(item: EmailOutbox, settings: Settings) -> None:
    message = _build_email(item, settings)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
        if settings.smtp_starttls:
            client.starttls()
        if settings.smtp_username and settings.smtp_password:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


def _claim_email(db: Session, item_id: UUID, now: datetime) -> EmailOutbox | None:
    item = db.scalar(
        select(EmailOutbox).where(EmailOutbox.id == item_id).with_for_update()
    )
    if item is None or item.status not in {"pending", "retry"}:
        return None
    if item.next_attempt_at > now:
        return None
    item.status = "processing"
    item.processing_started_at = now
    item.attempt_count += 1
    db.commit()
    return item


def dispatch_pending_emails(db: Session, *, limit: int = 25) -> int:
    settings = get_settings()
    if not settings.email_enabled:
        return 0

    now = datetime.now(UTC)
    stale_before = now - timedelta(minutes=PROCESSING_TIMEOUT_MINUTES)
    stale_items = db.scalars(
        select(EmailOutbox).where(
            EmailOutbox.status == "processing",
            EmailOutbox.processing_started_at < stale_before,
        )
    ).all()
    for item in stale_items:
        item.status = "retry"
        item.processing_started_at = None
        item.next_attempt_at = now
    if stale_items:
        db.commit()

    item_ids = db.scalars(
        select(EmailOutbox.id)
        .where(
            EmailOutbox.status.in_({"pending", "retry"}),
            EmailOutbox.next_attempt_at <= now,
            EmailOutbox.attempt_count < settings.email_max_attempts,
        )
        .order_by(EmailOutbox.next_attempt_at, EmailOutbox.created_at)
        .limit(limit)
    ).all()

    sent = 0
    for item_id in item_ids:
        item = _claim_email(db, item_id, datetime.now(UTC))
        if item is None:
            continue
        try:
            _send_email(item, settings)
        except Exception as error:
            db.rollback()
            failed_item = db.get(EmailOutbox, item_id)
            if failed_item is None:
                continue
            exhausted = failed_item.attempt_count >= settings.email_max_attempts
            retry_seconds = min(
                settings.email_retry_base_seconds * (2 ** (failed_item.attempt_count - 1)),
                MAX_RETRY_SECONDS,
            )
            failed_item.status = "failed" if exhausted else "retry"
            failed_item.processing_started_at = None
            failed_item.next_attempt_at = datetime.now(UTC) + timedelta(seconds=retry_seconds)
            failed_item.last_error = f"{type(error).__name__}: {error}"[:2000]
            db.commit()
        else:
            db.rollback()
            sent_item = db.get(EmailOutbox, item_id)
            if sent_item is None:
                continue
            sent_item.status = "sent"
            sent_item.processing_started_at = None
            sent_item.sent_at = datetime.now(UTC)
            sent_item.last_error = None
            db.commit()
            sent += 1
    return sent
