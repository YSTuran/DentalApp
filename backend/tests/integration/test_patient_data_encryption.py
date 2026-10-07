import json
from os import getenv

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies.auth import get_current_user
from app.db.session import engine
from app.main import app
from app.models import AuditEvent, RoleCode
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


def test_patient_identity_is_encrypted_searchable_and_absent_from_audit(
    case_session_factory: sessionmaker[Session],
) -> None:
    clinic = create_clinic(case_session_factory, "CRYPT")
    dentist = create_user(case_session_factory, RoleCode.DENTIST, clinic.id)
    staff = create_user(case_session_factory, RoleCode.CLINIC_STAFF, clinic.id)
    admin = create_user(case_session_factory, RoleCode.SYSTEM_ADMIN)
    payload = create_case_payload(clinic, dentist)
    payload.update(patient_code="HST-GİZLİ-42", patient_name="Şifreli Hasta")
    app.dependency_overrides[get_current_user] = lambda: staff

    with TestClient(app) as client:
        created_response = client.post(
            "/api/cases",
            headers=csrf_headers(client),
            json=payload,
        )
        assert created_response.status_code == 201
        created = created_response.json()
        case_id = created["id"]
        assert created["patient_code"] == "HST-GİZLİ-42"
        assert created["patient_name"] == "Şifreli Hasta"

        update_response = client.patch(
            f"/api/cases/{case_id}",
            headers=csrf_headers(client),
            json={
                "patient_code": "HST-GİZLİ-43",
                "patient_name": "Yeni Şifreli Hasta",
                "reason": "Kimlik alanları düzeltildi",
            },
        )
        assert update_response.status_code == 200

        exact_search = client.get("/api/cases", params={"search": "hst-gi̇zli̇-43"})
        old_search = client.get("/api/cases", params={"search": "hst-gi̇zli̇-42"})
        partial_search = client.get("/api/cases", params={"search": "GİZLİ"})
        assert [item["id"] for item in exact_search.json()["items"]] == [case_id]
        assert old_search.json()["total"] == 0
        assert partial_search.json()["total"] == 0

        app.dependency_overrides[get_current_user] = lambda: admin
        admin_detail = client.get(f"/api/cases/{case_id}")
        assert admin_detail.status_code == 200
        assert "patient_name" not in admin_detail.json()
        assert admin_detail.json()["patient_code"] == "HST-GİZLİ-43"

    with case_session_factory() as session:
        encrypted = session.execute(
            text(
                """
                SELECT patient_code_encrypted, patient_name_encrypted, patient_code_lookup
                FROM cases WHERE id = :case_id
                """
            ),
            {"case_id": case_id},
        ).one()
        audits = list(
            session.scalars(select(AuditEvent).where(
                AuditEvent.entity_id == case_id,
                AuditEvent.action.in_({"case.created", "case.updated"}),
            )).all()
        )

    assert encrypted.patient_code_lookup is not None
    assert b"HST-G" not in bytes(encrypted.patient_code_encrypted)
    assert "Yeni Şifreli Hasta".encode() not in bytes(encrypted.patient_name_encrypted)
    assert {audit.action for audit in audits} == {"case.created", "case.updated"}
    audit_json = json.dumps(
        [
            {"before": audit.before_data, "after": audit.after_data}
            for audit in audits
        ],
        ensure_ascii=False,
        default=str,
    )
    assert "HST-GİZLİ-42" not in audit_json
    assert "HST-GİZLİ-43" not in audit_json
    assert "Şifreli Hasta" not in audit_json
    assert "Yeni Şifreli Hasta" not in audit_json

    case_columns = {column["name"] for column in inspect(engine).get_columns("cases")}
    assert "patient_code" not in case_columns
    assert "patient_name" not in case_columns
