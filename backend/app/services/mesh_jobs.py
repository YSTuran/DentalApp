import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import CaseFileVersion, MeshValidationStatus, User
from app.services.audit import record_audit_event
from app.services.local_storage import LocalFileStorage
from app.services.mesh_validation import (
    MeshInspectionError,
    MeshResourceLimitError,
    inspect_stl_isolated,
)

logger = logging.getLogger(__name__)


def process_mesh_validation(
    file_version_id: UUID,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    stale_before = now - timedelta(minutes=settings.mesh_validation_stale_minutes)

    with session_factory() as db:
        version = db.scalar(
            select(CaseFileVersion)
            .where(CaseFileVersion.id == file_version_id)
            .with_for_update()
        )
        if version is None:
            return "missing"
        if version.mesh_status in {MeshValidationStatus.VALID, MeshValidationStatus.INVALID}:
            return version.mesh_status.value
        if (
            version.mesh_validation_started_at is not None
            and version.mesh_validation_started_at > stale_before
        ):
            return "already_processing"
        if version.mesh_validation_attempts >= settings.mesh_validation_max_attempts:
            if version.mesh_status != MeshValidationStatus.FAILED:
                version.mesh_status = MeshValidationStatus.FAILED
                version.mesh_report = {"error": "mesh_validation_attempts_exhausted"}
                version.mesh_validated_at = now
                db.commit()
            return MeshValidationStatus.FAILED.value

        version.mesh_validation_attempts += 1
        claimed_attempt = version.mesh_validation_attempts
        version.mesh_validation_started_at = now
        storage_key = version.storage_key
        db.commit()

    try:
        path = LocalFileStorage(settings.storage_path).path_for(storage_key)
        result = inspect_stl_isolated(
            path,
            timeout_seconds=settings.mesh_validation_timeout_seconds,
        )
        error_code = None
        terminal_error = False
    except MeshResourceLimitError:
        result = None
        error_code = "mesh_resource_limit"
        terminal_error = True
    except MeshInspectionError:
        result = None
        error_code = "mesh_parse_failed"
        terminal_error = False
    except Exception:
        logger.exception("Mesh doğrulaması beklenmeyen bir hatayla sonuçlandı")
        result = None
        error_code = "mesh_validation_internal_error"
        terminal_error = False

    with session_factory() as db:
        version = db.scalar(
            select(CaseFileVersion)
            .where(CaseFileVersion.id == file_version_id)
            .with_for_update()
        )
        if version is None or version.mesh_validation_attempts != claimed_attempt:
            return "superseded"

        version.mesh_validation_started_at = None
        terminal = (
            result is not None
            or terminal_error
            or claimed_attempt >= settings.mesh_validation_max_attempts
        )
        if result is not None:
            version.mesh_status = result.status
            version.mesh_report = result.report
            version.mesh_validated_at = datetime.now(UTC)
        elif terminal:
            version.mesh_status = MeshValidationStatus.FAILED
            version.mesh_report = {
                "error": error_code,
                "attempts": claimed_attempt,
            }
            version.mesh_validated_at = datetime.now(UTC)
        else:
            version.mesh_status = MeshValidationStatus.PENDING
            version.mesh_report = {
                "error": error_code,
                "attempts": claimed_attempt,
                "retry_scheduled": True,
            }

        if terminal:
            actor = db.get(User, version.uploaded_by_user_id)
            record_audit_event(
                db,
                action="case.file_mesh_validated",
                entity_type="case_file_version",
                entity_id=version.id,
                actor=actor,
                clinic_id=version.case.clinic_id,
                after={
                    "mesh_status": version.mesh_status,
                    "mesh_report": version.mesh_report,
                    "attempts": version.mesh_validation_attempts,
                },
                context={"source": "celery", "case_id": version.case_id},
            )
        db.commit()
        return version.mesh_status.value


def pending_mesh_file_ids(
    db: Session,
    *,
    limit: int = 100,
) -> list[UUID]:
    settings = get_settings()
    stale_before = datetime.now(UTC) - timedelta(
        minutes=settings.mesh_validation_stale_minutes
    )
    return list(
        db.scalars(
            select(CaseFileVersion.id)
            .where(
                CaseFileVersion.mesh_status == MeshValidationStatus.PENDING,
                CaseFileVersion.mesh_validation_attempts
                < settings.mesh_validation_max_attempts,
                or_(
                    CaseFileVersion.mesh_validation_started_at.is_(None),
                    CaseFileVersion.mesh_validation_started_at <= stale_before,
                ),
            )
            .order_by(CaseFileVersion.created_at)
            .limit(limit)
        ).all()
    )
