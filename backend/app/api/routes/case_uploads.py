from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_csrf
from app.api.dependencies.cases import case_access
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.schemas.case import (
    CaseFileVersionResponse,
    UploadCompleteResponse,
    UploadCreateRequest,
    UploadSessionResponse,
)
from app.services.audit import record_audit_event
from app.services.cases import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
    append_upload_chunk,
    complete_upload,
    get_file_version_for_download,
    get_upload,
    start_upload,
)
from app.services.local_storage import LocalFileStorage, StorageError
from app.services.task_dispatch import enqueue_mesh_validation

router = APIRouter()


def _raise_upload_error(error: Exception) -> None:
    if isinstance(error, CaseNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="case_not_found",
        ) from error
    if isinstance(error, CaseAccessDeniedError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="case_access_denied",
        ) from error
    if isinstance(error, CaseConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail) from error
    if isinstance(error, CaseValidationError):
        detail: str | dict[str, object] = error.detail
        if error.context:
            detail = {"code": error.detail, **error.context}
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        ) from error
    raise error


def _upload_response(upload) -> UploadSessionResponse:
    response = UploadSessionResponse.model_validate(upload)
    response.chunk_max_bytes = get_settings().upload_chunk_max_bytes
    return response


async def _read_upload_chunk(request: Request, *, max_bytes: int) -> bytes:
    data = bytearray()
    async for block in request.stream():
        if len(data) + len(block) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail={"code": "case_upload_chunk_too_large", "max_bytes": max_bytes},
            )
        data.extend(block)
    return bytes(data)


@router.post(
    "/{case_id}/uploads",
    response_model=UploadSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_file_upload(
    case_id: UUID,
    payload: UploadCreateRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> UploadSessionResponse:
    try:
        upload = start_upload(
            db,
            case_id=case_id,
            payload=payload,
            actor=actor,
            request=request,
        )
    except (
        CaseNotFoundError,
        CaseAccessDeniedError,
        CaseConflictError,
        CaseValidationError,
    ) as error:
        _raise_upload_error(error)
    return _upload_response(upload)


@router.get(
    "/{case_id}/uploads/{upload_id}",
    response_model=UploadSessionResponse,
)
def get_file_upload(
    case_id: UUID,
    upload_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
) -> UploadSessionResponse:
    try:
        upload = get_upload(db, case_id=case_id, upload_id=upload_id, actor=actor)
    except (CaseNotFoundError, CaseAccessDeniedError) as error:
        _raise_upload_error(error)
    return _upload_response(upload)


@router.patch(
    "/{case_id}/uploads/{upload_id}",
    response_model=UploadSessionResponse,
)
async def upload_file_chunk(
    case_id: UUID,
    upload_id: UUID,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
    upload_offset: Annotated[int, Header(alias="Upload-Offset", ge=0)],
    content_length: Annotated[int | None, Header(alias="Content-Length", ge=0)] = None,
) -> UploadSessionResponse:
    settings = get_settings()
    if content_length is not None and content_length > settings.upload_chunk_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "code": "case_upload_chunk_too_large",
                "max_bytes": settings.upload_chunk_max_bytes,
            },
        )
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type not in {"application/octet-stream", "application/offset+octet-stream"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="case_upload_content_type_invalid",
        )
    data = await _read_upload_chunk(request, max_bytes=settings.upload_chunk_max_bytes)
    try:
        upload = append_upload_chunk(
            db,
            case_id=case_id,
            upload_id=upload_id,
            offset=upload_offset,
            data=data,
            actor=actor,
        )
    except (
        CaseNotFoundError,
        CaseAccessDeniedError,
        CaseConflictError,
        CaseValidationError,
    ) as error:
        _raise_upload_error(error)
    response.headers["Upload-Offset"] = str(upload.received_size)
    return _upload_response(upload)


@router.post(
    "/{case_id}/uploads/{upload_id}/complete",
    response_model=UploadCompleteResponse,
)
def complete_file_upload(
    case_id: UUID,
    upload_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> UploadCompleteResponse:
    try:
        upload, version, should_enqueue = complete_upload(
            db,
            case_id=case_id,
            upload_id=upload_id,
            actor=actor,
            request=request,
        )
    except (
        CaseNotFoundError,
        CaseAccessDeniedError,
        CaseConflictError,
        CaseValidationError,
    ) as error:
        _raise_upload_error(error)
    queued = enqueue_mesh_validation(version.id) if should_enqueue else False
    return UploadCompleteResponse(
        upload=_upload_response(upload),
        file_version=CaseFileVersionResponse.model_validate(version),
        validation_queued=queued,
    )


@router.get("/{case_id}/files/{file_version_id}", response_class=FileResponse)
def download_case_file(
    case_id: UUID,
    file_version_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(case_access)],
    purpose: Annotated[Literal["download", "preview"], Query()] = "download",
) -> FileResponse:
    try:
        case, version = get_file_version_for_download(
            db,
            case_id=case_id,
            file_version_id=file_version_id,
            actor=actor,
        )
        path = LocalFileStorage(get_settings().storage_path).path_for(version.storage_key)
        if not path.is_file():
            raise StorageError("Dosya bulunamadı.")
    except (CaseNotFoundError, CaseAccessDeniedError) as error:
        _raise_upload_error(error)
    except StorageError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="case_file_not_found",
        ) from error

    record_audit_event(
        db,
        action=(
            "case.file_previewed" if purpose == "preview" else "case.file_downloaded"
        ),
        entity_type="case_file_version",
        entity_id=version.id,
        actor=actor,
        clinic_id=case.clinic_id,
        context={
            "source": "api",
            "purpose": purpose,
            "case_id": case.id,
            "kind": version.kind,
            "version_number": version.version_number,
        },
        request=request,
    )
    db.commit()

    safe_filename = f"{case.case_number}-{version.kind.value}-v{version.version_number}.stl"
    return FileResponse(
        path,
        media_type="model/stl",
        filename=safe_filename,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
