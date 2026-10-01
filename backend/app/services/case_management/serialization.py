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
        for file_version in response.file_versions:
            file_version.original_filename = None
    return response
