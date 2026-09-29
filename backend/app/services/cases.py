"""Public facade for the case management service."""

from app.services.case_management.commands import create_case, update_case
from app.services.case_management.exceptions import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
)
from app.services.case_management.queries import (
    get_visible_case,
    list_case_history,
    list_visible_cases,
)
from app.services.case_management.serialization import case_to_response
from app.services.case_management.workflow import cancel_case, submit_case

__all__ = [
    "CaseAccessDeniedError",
    "CaseConflictError",
    "CaseNotFoundError",
    "CaseValidationError",
    "cancel_case",
    "case_to_response",
    "create_case",
    "get_visible_case",
    "list_case_history",
    "list_visible_cases",
    "submit_case",
    "update_case",
]
