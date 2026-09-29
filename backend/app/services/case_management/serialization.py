from app.models import DentalCase, User
from app.schemas.case import CaseResponse
from app.services.case_management.access import can_view_patient_name


def case_to_response(case: DentalCase, *, actor: User) -> CaseResponse:
    response = CaseResponse.model_validate(case)
    if not can_view_patient_name(actor, case):
        response.patient_name = None
    return response
