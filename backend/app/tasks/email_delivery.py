from app.core.celery import celery_app
from app.db.session import SessionLocal
from app.services.email_dispatch import dispatch_pending_emails


@celery_app.task(name="email.dispatch_pending", ignore_result=True)
def dispatch_pending_email_messages() -> None:
    with SessionLocal() as db:
        dispatch_pending_emails(db)
