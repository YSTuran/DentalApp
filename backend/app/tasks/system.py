from redis import Redis

from app.core.celery import celery_app
from app.core.config import get_settings

BACKGROUND_HEARTBEAT_KEY = "dentalapp:background-services:heartbeat"


@celery_app.task(name="system.heartbeat", ignore_result=True)
def background_services_heartbeat() -> None:
    client = Redis.from_url(get_settings().redis_url)
    try:
        client.set(BACKGROUND_HEARTBEAT_KEY, "ok", ex=60)
    finally:
        client.close()
