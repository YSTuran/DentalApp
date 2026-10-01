import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    CaseFileKind,
    CaseFileVersion,
    CaseStatus,
    CaseUploadSession,
    MeshValidationStatus,
    RoleCode,
    UploadStatus,
    User,
)
from app.schemas.case import UploadCreateRequest
from app.services.audit import record_audit_event
from app.services.case_management.access import has_role, require_case_visibility
from app.services.case_management.commands import EDITABLE_CASE_STATUSES
from app.services.case_management.exceptions import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
)
from app.services.case_management.repository import load_case
from app.services.case_management.validation import validate_clinic
from app.services.local_storage import LocalFileStorage, StorageError

logger = logging.getLogger(__name__)
DESIGN_UPLOAD_STATUSES = frozenset(
    {CaseStatus.LAB_DESIGN, CaseStatus.DESIGN_REVISION_REQUESTED}
)


def _storage() -> LocalFileStorage:
    return LocalFileStorage(get_settings().storage_path)


def _require_upload_access(case, actor: User, kind: CaseFileKind) -> None:
    require_case_visibility(actor, case)
    if kind == CaseFileKind.SCAN:
        if case.status not in EDITABLE_CASE_STATUSES:
            raise CaseConflictError("case_scan_upload_not_allowed")
        if actor.id not in {case.created_by_user_id, case.responsible_dentist_user_id}:
            raise CaseAccessDeniedError
        return

    if case.status not in DESIGN_UPLOAD_STATUSES:
        raise CaseConflictError("case_design_upload_not_allowed")
    if not has_role(actor, RoleCode.TECHNICIAN):
        raise CaseAccessDeniedError


def _load_upload(
    db: Session,
    *,
    case_id: UUID,
    upload_id: UUID,
    for_update: bool = False,
) -> CaseUploadSession:
    statement = select(CaseUploadSession).where(
        CaseUploadSession.id == upload_id,
        CaseUploadSession.case_id == case_id,
    )
    if for_update:
        statement = statement.with_for_update()
    upload = db.scalar(statement)
    if upload is None:
        raise CaseNotFoundError
    return upload


def _is_expired(upload: CaseUploadSession) -> bool:
    return upload.expires_at <= datetime.now(UTC)


def _expire_upload(db: Session, upload: CaseUploadSession, *, actor: User) -> None:
    if upload.status in {UploadStatus.COMPLETED, UploadStatus.EXPIRED}:
        return
    upload.status = UploadStatus.EXPIRED
    upload.failure_reason = "upload_expired"
    record_audit_event(
        db,
        action="case.file_upload_expired",
        entity_type="case_upload_session",
        entity_id=upload.id,
        actor=actor,
        clinic_id=upload.case.clinic_id,
        after={"status": UploadStatus.EXPIRED, "received_size": upload.received_size},
        context={"source": "api", "case_id": upload.case_id, "kind": upload.kind},
    )
    db.commit()
    _storage().remove(upload.temp_storage_key)


def start_upload(
    db: Session,
    *,
    case_id: UUID,
    payload: UploadCreateRequest,
    actor: User,
    request: Request,
) -> CaseUploadSession:
    settings = get_settings()
    if payload.expected_size > settings.upload_max_bytes:
        raise CaseValidationError(
            "case_file_too_large",
            context={"max_bytes": settings.upload_max_bytes},
        )

    case = load_case(db, case_id, for_update=True)
    validate_clinic(db, case.clinic_id)
    _require_upload_access(case, actor, payload.kind)

    upload_id = uuid4()
    temporary_key = f"uploads/{case.id}/{upload_id}.part"
    storage = _storage()
    try:
        storage.create_empty(temporary_key)
    except StorageError as error:
        raise CaseConflictError("case_upload_storage_error") from error

    upload = CaseUploadSession(
        id=upload_id,
        case_id=case.id,
        kind=payload.kind,
        original_filename=payload.original_filename,
        expected_size=payload.expected_size,
        expected_sha256=payload.expected_sha256,
        temp_storage_key=temporary_key,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.upload_session_hours),
        created_by_user_id=actor.id,
    )
    try:
        db.add(upload)
        db.flush()
        record_audit_event(
            db,
            action="case.file_upload_started",
            entity_type="case_upload_session",
            entity_id=upload.id,
            actor=actor,
            clinic_id=case.clinic_id,
            after={
                "case_id": case.id,
                "kind": upload.kind,
                "expected_size": upload.expected_size,
            },
            context={"source": "api"},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        storage.remove(temporary_key)
        raise
    db.refresh(upload)
    return upload


def get_upload(
    db: Session,
    *,
    case_id: UUID,
    upload_id: UUID,
    actor: User,
) -> CaseUploadSession:
    case = load_case(db, case_id)
    require_case_visibility(actor, case)
    upload = _load_upload(db, case_id=case_id, upload_id=upload_id)
    if upload.created_by_user_id != actor.id:
        raise CaseAccessDeniedError
    return upload


def append_upload_chunk(
    db: Session,
    *,
    case_id: UUID,
    upload_id: UUID,
    offset: int,
    data: bytes,
    actor: User,
) -> CaseUploadSession:
    settings = get_settings()
    if not data:
        raise CaseValidationError("case_upload_chunk_empty")
    if len(data) > settings.upload_chunk_max_bytes:
        raise CaseValidationError(
            "case_upload_chunk_too_large",
            context={"max_bytes": settings.upload_chunk_max_bytes},
        )

    case = load_case(db, case_id, for_update=True)
    validate_clinic(db, case.clinic_id)
    upload = _load_upload(db, case_id=case_id, upload_id=upload_id, for_update=True)
    if upload.created_by_user_id != actor.id:
        raise CaseAccessDeniedError
    _require_upload_access(case, actor, upload.kind)
    if _is_expired(upload):
        _expire_upload(db, upload, actor=actor)
        raise CaseConflictError("case_upload_expired")
    if upload.status not in {UploadStatus.PENDING, UploadStatus.UPLOADING}:
        raise CaseConflictError("case_upload_not_writable")
    if offset != upload.received_size:
        raise CaseConflictError("case_upload_offset_mismatch")
    if offset + len(data) > upload.expected_size:
        raise CaseValidationError("case_upload_size_exceeded")

    storage = _storage()
    try:
        resulting_size = storage.append(upload.temp_storage_key, offset=offset, data=data)
        if resulting_size != offset + len(data):
            raise StorageError("Yazılan parça boyutu doğrulanamadı.")
        upload.received_size = resulting_size
        upload.status = UploadStatus.UPLOADING
        db.commit()
    except StorageError as error:
        db.rollback()
        raise CaseConflictError("case_upload_storage_error") from error
    except Exception:
        db.rollback()
        try:
            storage.truncate(upload.temp_storage_key, offset)
        except StorageError:
            logger.exception("Başarısız veritabanı işleminden sonra geçici dosya kısaltılamadı")
        raise
    db.refresh(upload)
    return upload


def complete_upload(
    db: Session,
    *,
    case_id: UUID,
    upload_id: UUID,
    actor: User,
    request: Request,
) -> tuple[CaseUploadSession, CaseFileVersion, bool]:
    case = load_case(db, case_id, for_update=True)
    require_case_visibility(actor, case)
    upload = _load_upload(db, case_id=case_id, upload_id=upload_id, for_update=True)
    if upload.created_by_user_id != actor.id:
        raise CaseAccessDeniedError
    if upload.status == UploadStatus.COMPLETED:
        version = db.get(CaseFileVersion, upload.completed_file_version_id)
        if version is None:
            raise CaseConflictError("case_upload_completion_inconsistent")
        return upload, version, False

    validate_clinic(db, case.clinic_id)
    _require_upload_access(case, actor, upload.kind)
    if _is_expired(upload):
        _expire_upload(db, upload, actor=actor)
        raise CaseConflictError("case_upload_expired")
    if upload.status not in {UploadStatus.PENDING, UploadStatus.UPLOADING}:
        raise CaseConflictError("case_upload_not_completable")
    if upload.received_size != upload.expected_size:
        raise CaseConflictError("case_upload_incomplete")

    storage = _storage()
    try:
        if storage.size(upload.temp_storage_key) != upload.expected_size:
            raise StorageError("Geçici dosya boyutu yükleme kaydıyla uyuşmuyor.")
        digest = storage.sha256(upload.temp_storage_key)
    except StorageError as error:
        raise CaseConflictError("case_upload_storage_error") from error

    if upload.expected_sha256 is not None and digest != upload.expected_sha256:
        upload.status = UploadStatus.FAILED
        upload.failure_reason = "sha256_mismatch"
        record_audit_event(
            db,
            action="case.file_upload_failed",
            entity_type="case_upload_session",
            entity_id=upload.id,
            actor=actor,
            clinic_id=case.clinic_id,
            after={"status": UploadStatus.FAILED, "reason": upload.failure_reason},
            context={"source": "api", "case_id": case.id, "kind": upload.kind},
            request=request,
        )
        db.commit()
        storage.remove(upload.temp_storage_key)
        raise CaseValidationError("case_upload_sha256_mismatch")

    current_version = db.scalar(
        select(func.max(CaseFileVersion.version_number)).where(
            CaseFileVersion.case_id == case.id,
            CaseFileVersion.kind == upload.kind,
        )
    )
    version_number = (current_version or 0) + 1
    file_version_id = uuid4()
    final_key = (
        f"cases/{case.id}/{upload.kind.value}/"
        f"v{version_number}-{file_version_id}.stl"
    )
    try:
        storage.promote(upload.temp_storage_key, final_key)
    except StorageError as error:
        raise CaseConflictError("case_upload_storage_error") from error

    version = CaseFileVersion(
        id=file_version_id,
        case_id=case.id,
        kind=upload.kind,
        version_number=version_number,
        original_filename=upload.original_filename,
        storage_key=final_key,
        size_bytes=upload.expected_size,
        sha256=digest,
        mesh_status=MeshValidationStatus.PENDING,
        uploaded_by_user_id=actor.id,
    )
    try:
        db.add(version)
        db.flush()
        upload.status = UploadStatus.COMPLETED
        upload.completed_file_version_id = version.id
        upload.failure_reason = None
        record_audit_event(
            db,
            action="case.file_uploaded",
            entity_type="case_file_version",
            entity_id=version.id,
            actor=actor,
            clinic_id=case.clinic_id,
            after={
                "case_id": case.id,
                "kind": version.kind,
                "version_number": version.version_number,
                "size_bytes": version.size_bytes,
                "sha256": version.sha256,
                "mesh_status": version.mesh_status,
            },
            context={"source": "api", "upload_session_id": upload.id},
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        try:
            storage.restore(final_key, upload.temp_storage_key)
        except StorageError:
            logger.exception("Başarısız veritabanı işleminden sonra dosya geri taşınamadı")
        raise
    db.refresh(upload)
    db.refresh(version)
    return upload, version, True


def get_file_version_for_download(
    db: Session,
    *,
    case_id: UUID,
    file_version_id: UUID,
    actor: User,
) -> tuple[object, CaseFileVersion]:
    case = load_case(db, case_id)
    require_case_visibility(actor, case)
    version = db.scalar(
        select(CaseFileVersion).where(
            CaseFileVersion.id == file_version_id,
            CaseFileVersion.case_id == case_id,
        )
    )
    if version is None:
        raise CaseNotFoundError
    return case, version


def expire_stale_uploads(db: Session, *, limit: int = 100) -> int:
    uploads = list(
        db.scalars(
            select(CaseUploadSession)
            .where(
                CaseUploadSession.status.in_(
                    [UploadStatus.PENDING, UploadStatus.UPLOADING]
                ),
                CaseUploadSession.expires_at <= datetime.now(UTC),
            )
            .order_by(CaseUploadSession.expires_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )
    if not uploads:
        return 0

    storage = _storage()
    for upload in uploads:
        upload.status = UploadStatus.EXPIRED
        upload.failure_reason = "upload_expired"
        record_audit_event(
            db,
            action="case.file_upload_expired",
            entity_type="case_upload_session",
            entity_id=upload.id,
            clinic_id=upload.case.clinic_id,
            after={"status": UploadStatus.EXPIRED, "received_size": upload.received_size},
            context={
                "source": "celery",
                "case_id": upload.case_id,
                "kind": upload.kind,
            },
        )
    db.commit()
    for upload in uploads:
        try:
            storage.remove(upload.temp_storage_key)
        except StorageError:
            logger.exception("Süresi dolan geçici yükleme dosyası temizlenemedi")
    return len(uploads)
