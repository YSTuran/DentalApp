import hashlib
from os import getenv
from pathlib import Path
from uuid import UUID

import pytest
import trimesh
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.core.config import get_settings
from app.main import app
from app.models import RoleCode
from app.services.mesh_jobs import process_mesh_validation
from tests.integration.case_test_support import (
    create_case_payload,
    create_clinic,
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


def test_resumable_upload_validation_download_and_submit(
    case_session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    previous_storage_path = settings.storage_path
    settings.storage_path = tmp_path
    monkeypatch.setattr(
        "app.api.routes.case_uploads.enqueue_mesh_validation",
        lambda _file_version_id: True,
    )

    clinic = create_clinic(case_session_factory, "UPLOAD")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    app.dependency_overrides[get_current_user] = lambda: dentist
    stl_bytes = trimesh.creation.icosphere(subdivisions=1, radius=10).export(
        file_type="stl"
    )
    digest = hashlib.sha256(stl_bytes).hexdigest()

    try:
        with TestClient(app) as client:
            headers = csrf_headers(client)
            create_response = client.post(
                "/api/cases",
                headers=headers,
                json=create_case_payload(clinic, dentist),
            )
            assert create_response.status_code == 201
            case_id = create_response.json()["id"]

            upload_response = client.post(
                f"/api/cases/{case_id}/uploads",
                headers=headers,
                json={
                    "kind": "scan",
                    "original_filename": "demo-scan.stl",
                    "expected_size": len(stl_bytes),
                    "expected_sha256": digest,
                },
            )
            assert upload_response.status_code == 201
            upload_id = upload_response.json()["id"]
            split_at = len(stl_bytes) // 2

            first_chunk = client.patch(
                f"/api/cases/{case_id}/uploads/{upload_id}",
                headers={
                    **headers,
                    "Content-Type": "application/offset+octet-stream",
                    "Upload-Offset": "0",
                },
                content=stl_bytes[:split_at],
            )
            assert first_chunk.status_code == 200
            assert first_chunk.json()["received_size"] == split_at

            status_response = client.get(
                f"/api/cases/{case_id}/uploads/{upload_id}"
            )
            assert status_response.status_code == 200
            assert status_response.json()["received_size"] == split_at

            wrong_offset = client.patch(
                f"/api/cases/{case_id}/uploads/{upload_id}",
                headers={
                    **headers,
                    "Content-Type": "application/offset+octet-stream",
                    "Upload-Offset": "0",
                },
                content=stl_bytes[split_at:],
            )
            assert wrong_offset.status_code == 409
            assert wrong_offset.json()["detail"] == "case_upload_offset_mismatch"

            second_chunk = client.patch(
                f"/api/cases/{case_id}/uploads/{upload_id}",
                headers={
                    **headers,
                    "Content-Type": "application/offset+octet-stream",
                    "Upload-Offset": str(split_at),
                },
                content=stl_bytes[split_at:],
            )
            assert second_chunk.status_code == 200
            assert second_chunk.json()["received_size"] == len(stl_bytes)

            complete_response = client.post(
                f"/api/cases/{case_id}/uploads/{upload_id}/complete",
                headers=headers,
            )
            assert complete_response.status_code == 200
            completed = complete_response.json()
            assert completed["upload"]["status"] == "completed"
            assert completed["file_version"]["version_number"] == 1
            assert completed["file_version"]["mesh_status"] == "pending"
            assert completed["validation_queued"] is True
            file_version_id = completed["file_version"]["id"]

            repeated_complete = client.post(
                f"/api/cases/{case_id}/uploads/{upload_id}/complete",
                headers=headers,
            )
            assert repeated_complete.status_code == 200
            assert repeated_complete.json()["file_version"]["id"] == file_version_id
            assert repeated_complete.json()["validation_queued"] is False

        result = process_mesh_validation(
            UUID(file_version_id),
            session_factory=case_session_factory,
        )
        assert result == "valid"

        with TestClient(app) as client:
            headers = csrf_headers(client)
            detail_response = client.get(f"/api/cases/{case_id}")
            assert detail_response.status_code == 200
            assert detail_response.json()["file_versions"][0]["mesh_status"] == "valid"

            download_response = client.get(
                f"/api/cases/{case_id}/files/{file_version_id}"
            )
            assert download_response.status_code == 200
            assert download_response.content == stl_bytes
            assert "demo-scan.stl" not in download_response.headers["content-disposition"]

            submit_response = client.post(
                f"/api/cases/{case_id}/submit",
                headers=headers,
            )
            assert submit_response.status_code == 200
            assert submit_response.json()["status"] == "manager_review"
    finally:
        settings.storage_path = previous_storage_path
