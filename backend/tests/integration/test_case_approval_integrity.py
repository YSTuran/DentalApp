from os import getenv
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    CaseApproval,
    CaseApprovalType,
    CaseDecision,
    CaseDetail,
    CaseFileKind,
    CaseFileVersion,
    CaseStatus,
    DentalCase,
    MeshValidationStatus,
    RoleCode,
)
from tests.integration.case_test_support import create_clinic, create_user

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def _create_case(
    factory: sessionmaker[Session],
    *,
    clinic_id,
    dentist_id,
) -> DentalCase:
    with factory.begin() as session:
        case = DentalCase(
            case_number=f"INTEGRITY-{uuid4().hex[:12]}",
            clinic_id=clinic_id,
            created_by_user_id=dentist_id,
            responsible_dentist_user_id=dentist_id,
            status=CaseStatus.MANAGER_REVIEW,
            details=CaseDetail(),
        )
        session.add(case)
        session.flush()
    return case


def _create_file(
    factory: sessionmaker[Session],
    *,
    case_id,
    user_id,
    kind: CaseFileKind,
    locked: bool = False,
) -> CaseFileVersion:
    with factory.begin() as session:
        file_version = CaseFileVersion(
            case_id=case_id,
            kind=kind,
            version_number=1,
            original_filename=f"{kind.value}.stl",
            storage_key=f"test/{uuid4().hex}.stl",
            size_bytes=1024,
            sha256="a" * 64,
            mesh_status=MeshValidationStatus.VALID,
            uploaded_by_user_id=user_id,
            is_locked=locked,
        )
        session.add(file_version)
        session.flush()
    return file_version


def test_approval_cannot_reference_file_from_another_case(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "APPROVAL-CASE")
    dentist = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    source_case = _create_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
    )
    target_case = _create_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
    )
    scan = _create_file(
        case_session_factory,
        case_id=source_case.id,
        user_id=dentist.id,
        kind=CaseFileKind.SCAN,
    )

    with pytest.raises(IntegrityError):
        with case_session_factory.begin() as session:
            session.add(
                CaseApproval(
                    case_id=target_case.id,
                    approval_type=CaseApprovalType.MANAGER_SCAN,
                    decision=CaseDecision.APPROVED,
                    file_version_id=scan.id,
                    actor_user_id=dentist.id,
                )
            )


def test_manager_approval_cannot_reference_design_file(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "APPROVAL-KIND")
    dentist = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    case = _create_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
    )
    design = _create_file(
        case_session_factory,
        case_id=case.id,
        user_id=dentist.id,
        kind=CaseFileKind.DESIGN,
    )

    with pytest.raises(DBAPIError, match="yalnızca tarama"):
        with case_session_factory.begin() as session:
            session.add(
                CaseApproval(
                    case_id=case.id,
                    approval_type=CaseApprovalType.MANAGER_SCAN,
                    decision=CaseDecision.APPROVED,
                    file_version_id=design.id,
                    actor_user_id=dentist.id,
                )
            )


def test_locked_file_version_cannot_be_changed(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "LOCKED-FILE")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    case = _create_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
    )
    scan = _create_file(
        case_session_factory,
        case_id=case.id,
        user_id=dentist.id,
        kind=CaseFileKind.SCAN,
        locked=True,
    )

    with pytest.raises(DBAPIError, match="Kilitli vaka dosyası değiştirilemez"):
        with case_session_factory.begin() as session:
            stored = session.get(CaseFileVersion, scan.id)
            assert stored is not None
            stored.original_filename = "changed.stl"
