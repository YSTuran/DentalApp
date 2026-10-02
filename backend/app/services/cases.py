"""Public facade for the case management service."""

from app.services.case_management.commands import create_case, update_case
from app.services.case_management.design_workflow import dentist_decide_design, submit_design
from app.services.case_management.exceptions import (
    CaseAccessDeniedError,
    CaseConflictError,
    CaseNotFoundError,
    CaseValidationError,
)
from app.services.case_management.queries import (
    get_visible_case,
    list_case_create_options,
    list_case_history,
    list_visible_cases,
)
from app.services.case_management.serialization import case_to_response
from app.services.case_management.uploads import (
    append_upload_chunk,
    complete_upload,
    get_file_version_for_download,
    get_upload,
    start_upload,
)
from app.services.case_management.workflow import cancel_case, manager_decide_case, submit_case

__all__ = [
    "CaseAccessDeniedError",
    "CaseConflictError",
    "CaseNotFoundError",
    "CaseValidationError",
    "append_upload_chunk",
    "cancel_case",
    "case_to_response",
    "complete_upload",
    "create_case",
    "dentist_decide_design",
    "get_visible_case",
    "get_file_version_for_download",
    "get_upload",
    "list_case_create_options",
    "list_case_history",
    "list_visible_cases",
    "manager_decide_case",
    "submit_case",
    "submit_design",
    "start_upload",
    "update_case",
]
