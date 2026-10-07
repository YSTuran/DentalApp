from app.core.celery import celery_app
from app.db.session import SessionLocal
from app.services.case_waiting import create_overdue_case_alerts


@celery_app.task(name="cases.warn_overdue", ignore_result=True)
def warn_overdue_cases() -> None:
    with SessionLocal() as db:
        create_overdue_case_alerts(db)
