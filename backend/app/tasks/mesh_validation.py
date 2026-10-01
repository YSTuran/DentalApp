from uuid import UUID

from app.core.celery import celery_app
from app.db.session import SessionLocal
from app.services.mesh_jobs import pending_mesh_file_ids, process_mesh_validation


@celery_app.task(name="mesh.validate_file", ignore_result=True)
def validate_mesh_file(file_version_id: str) -> None:
    process_mesh_validation(UUID(file_version_id))


@celery_app.task(name="mesh.dispatch_pending", ignore_result=True)
def dispatch_pending_mesh_validations() -> None:
    with SessionLocal() as db:
        file_ids = pending_mesh_file_ids(db)
    for file_id in file_ids:
        validate_mesh_file.delay(str(file_id))
