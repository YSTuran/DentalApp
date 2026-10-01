from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "dentalapp",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.mesh_validation", "app.tasks.uploads"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Istanbul",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "dispatch-pending-mesh-validations": {
            "task": "mesh.dispatch_pending",
            "schedule": 30.0,
        },
        "expire-stale-file-uploads": {
            "task": "uploads.expire_stale",
            "schedule": 3600.0,
        },
    },
)
