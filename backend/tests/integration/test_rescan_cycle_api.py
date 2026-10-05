from os import getenv
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models import CaseFileKind, CaseFileVersion, MeshValidationStatus, RoleCode
from tests.integration.case_test_support import (
    create_clinic,
    create_ready_for_production_case,
    create_user,
    csrf_headers,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
        reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
    ),
]


def test_rescan_requires_new_scan_and_new_design(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "RESCAN")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    manager = create_user(case_session_factory, RoleCode.MANAGING_DENTIST, clinic.id)
    staff = create_user(case_session_factory, RoleCode.CLINIC_STAFF, clinic.id)
    technician = create_user(case_session_factory, RoleCode.TECHNICIAN)
    case, old_design = create_ready_for_production_case(
        case_session_factory,
        clinic_id=clinic.id,
        dentist_id=dentist.id,
        manager_id=manager.id,
        technician_id=technician.id,
    )

    with TestClient(app) as client:
        headers = csrf_headers(client)
        app.dependency_overrides[get_current_user] = lambda: technician
        client.post(
            f"/api/cases/{case.id}/production/start",
            headers=headers,
            json={"design_file_version_id": str(old_design.id)},
        )
        run_id = client.get(f"/api/cases/{case.id}/operations").json()["production_runs"][0]["id"]
        client.post(
            f"/api/cases/{case.id}/production/complete",
            headers=headers,
            json={
                "production_run_id": run_id,
                "material": "PET-G",
                "lot_number": "RESCAN-LOT",
                "quantity": 1,
            },
        )
        client.post(
            f"/api/cases/{case.id}/shipments",
            headers=headers,
            json={
                "production_run_id": run_id,
                "carrier": "Demo Kargo",
                "tracking_number": uuid4().hex,
            },
        )
        shipment_id = client.get(f"/api/cases/{case.id}/operations").json()["shipments"][0]["id"]

        app.dependency_overrides[get_current_user] = lambda: staff
        client.post(
            f"/api/cases/{case.id}/delivery-confirmation",
            headers=headers,
            json={"shipment_id": shipment_id},
        )
        app.dependency_overrides[get_current_user] = lambda: technician
        client.post(
            f"/api/cases/{case.id}/returns",
            headers=headers,
            json={
                "shipment_id": shipment_id,
                "reason_code": "fit_issue",
                "reason": "Yeni ağız içi tarama gerekli.",
            },
        )
        return_operations = client.get(f"/api/cases/{case.id}/operations").json()
        receipt_id = return_operations["return_receipts"][0]["id"]
        app.dependency_overrides[get_current_user] = lambda: manager
        decision = client.post(
            f"/api/cases/{case.id}/return-decision",
            headers=headers,
            json={
                "return_receipt_id": receipt_id,
                "resolution": "rescan",
                "reason": "Ölçü değiştiği için yeni tarama alınmalı.",
            },
        )
        assert decision.status_code == 200
        assert decision.json()["status"] == "rescan_requested"

        app.dependency_overrides[get_current_user] = lambda: dentist
        old_scan_submit = client.post(f"/api/cases/{case.id}/submit", headers=headers)
        assert old_scan_submit.status_code == 422
        assert old_scan_submit.json()["detail"] == "case_rescan_required"

        with case_session_factory.begin() as session:
            new_scan = CaseFileVersion(
                case_id=case.id,
                kind=CaseFileKind.SCAN,
                version_number=2,
                original_filename="scan-v2.stl",
                storage_key=f"test/{case.id}/scan-v2.stl",
                size_bytes=2048,
                sha256="c" * 64,
                mesh_status=MeshValidationStatus.VALID,
                uploaded_by_user_id=dentist.id,
            )
            session.add(new_scan)
            session.flush()

        submitted = client.post(f"/api/cases/{case.id}/submit", headers=headers)
        assert submitted.status_code == 200, submitted.json()
        app.dependency_overrides[get_current_user] = lambda: manager
        approved = client.post(
            f"/api/cases/{case.id}/manager-decision",
            headers=headers,
            json={"decision": "approved", "file_version_id": str(new_scan.id)},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "lab_design"

        app.dependency_overrides[get_current_user] = lambda: technician
        old_design_submit = client.post(
            f"/api/cases/{case.id}/design-submit",
            headers=headers,
            json={"file_version_id": str(old_design.id)},
        )
        assert old_design_submit.status_code == 422
        assert old_design_submit.json()["detail"] == "case_new_design_required"
