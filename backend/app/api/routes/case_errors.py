from typing import NoReturn

from fastapi import HTTPException, status

from app.services.cases import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
)


def raise_case_service_error(error: Exception) -> NoReturn:
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.detail,
        ) from error
    if isinstance(error, CaseValidationError):
        detail: str | dict[str, object] = error.detail
        if error.context:
            detail = {"code": error.detail, **error.context}
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        ) from error
    raise error
