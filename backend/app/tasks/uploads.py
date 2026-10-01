from app.core.celery import celery_app
from app.db.session import SessionLocal
from app.services.case_management.uploads import expire_stale_uploads


@celery_app.task(name="uploads.expire_stale", ignore_result=True)
def expire_stale_file_uploads() -> None:
    with SessionLocal() as db:
        expire_stale_uploads(db)
