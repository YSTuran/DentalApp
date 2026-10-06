from app.models import DentalCase, User
from app.schemas.case import CaseResponse
from app.services.case_management.access import can_view_patient_name


def case_to_response(case: DentalCase, *, actor: User) -> CaseResponse:
    response = CaseResponse.model_validate(
        {
            **case.__dict__,
            "clinic_name": case.clinic.name,
            "responsible_dentist_name": case.responsible_dentist.full_name,
        }
    )
    if not can_view_patient_name(actor, case):
        response.patient_name = None
        response.created_by_user_id = None
        response.responsible_dentist_user_id = None
        response.details.special_notes = None
        response.details.extra_fields = {}
        for file_version in response.file_versions:
            file_version.original_filename = None
            file_version.uploaded_by_user_id = None
        for approval in response.approvals:
            approval.actor_user_id = None
    return response
