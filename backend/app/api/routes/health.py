from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.firebase import check_firebase
from app.schemas.health import HealthResponse, LivenessResponse
from app.services.health import check_database, check_redis

router = APIRouter()


@router.get("/live", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    settings = get_settings()
    return LivenessResponse(api="ok", demo_mode=settings.demo_mode)


@router.get(
    "",
    response_model=HealthResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
)
def readiness(response: Response) -> HealthResponse:
    settings = get_settings()
    database_ok = check_database()
    redis_ok = check_redis()
    firebase_ok = check_firebase()

    if not database_ok or not redis_ok or not firebase_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        api="ok",
        database="ok" if database_ok else "error",
        redis="ok" if redis_ok else "error",
        firebase="ok" if firebase_ok else "error",
        demo_mode=settings.demo_mode,
    )
