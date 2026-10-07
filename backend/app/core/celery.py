from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "dentalapp",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.case_waiting",
        "app.tasks.email_delivery",
        "app.tasks.mesh_validation",
        "app.tasks.system",
        "app.tasks.uploads",
    ],
)
celery_app.conf.update(
    task_default_queue="default",
    task_routes={
        "mesh.validate_file": {"queue": "mesh"},
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Istanbul",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=settings.mesh_validation_timeout_seconds + 30,
    task_time_limit=settings.mesh_validation_timeout_seconds + 60,
    beat_schedule={
        "dispatch-pending-mesh-validations": {
            "task": "mesh.dispatch_pending",
            "schedule": 30.0,
        },
        "expire-stale-file-uploads": {
            "task": "uploads.expire_stale",
            "schedule": 3600.0,
        },
        "dispatch-pending-email-messages": {
            "task": "email.dispatch_pending",
            "schedule": 15.0,
        },
        "warn-overdue-cases": {
            "task": "cases.warn_overdue",
            "schedule": 900.0,
        },
        "background-services-heartbeat": {
            "task": "system.heartbeat",
            "schedule": 15.0,
        },
    },
)
