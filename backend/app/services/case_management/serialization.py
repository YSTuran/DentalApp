from app.models import DentalCase, User
from app.schemas.case import CaseResponse
from app.services.case_management.access import can_view_patient_name
from app.services.case_management.patient_data import get_patient_code, get_patient_name


def case_to_response(case: DentalCase, *, actor: User) -> CaseResponse:
    response = CaseResponse.model_validate(
        {
            **case.__dict__,
            "clinic_name": case.clinic.name,
            "responsible_dentist_name": case.responsible_dentist.full_name,
            "patient_code": get_patient_code(case),
            "patient_name": get_patient_name(case) if can_view_patient_name(actor, case) else None,
        }
    )
    if not can_view_patient_name(actor, case):
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
