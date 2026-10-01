import logging
from uuid import UUID

from app.core.celery import celery_app

logger = logging.getLogger(__name__)


def enqueue_mesh_validation(file_version_id: UUID) -> bool:
    try:
        celery_app.send_task("mesh.validate_file", args=[str(file_version_id)])
    except Exception:
        logger.warning(
            "Mesh doğrulama işi hemen kuyruğa alınamadı; periyodik tarayıcı tekrar deneyecek",
            exc_info=True,
        )
        return False
    return True
