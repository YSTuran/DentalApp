from os import getenv
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import engine

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
    reason="Set RUN_DATABASE_INTEGRATION_TESTS=1 to run database integration tests.",
)
@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE case_status_history SET action = 'changed' WHERE id = :history_id",
        "DELETE FROM case_status_history WHERE id = :history_id",
    ],
)
def test_case_history_rejects_mutation(mutation: str) -> None:
    clinic_id = uuid4()
    user_id = uuid4()
    case_id = uuid4()
    history_id = uuid4()

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO clinics (id, code, name)
                    VALUES (:clinic_id, :code, 'Immutable Case Clinic')
                    """
                ),
                {"clinic_id": clinic_id, "code": f"IMM-{uuid4().hex[:8]}"},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO users (id, email, firebase_uid, full_name)
                    VALUES (:user_id, :email, :firebase_uid, 'Immutable Case User')
                    """
                ),
                {
                    "user_id": user_id,
                    "email": f"{uuid4().hex}@example.invalid",
                    "firebase_uid": uuid4().hex,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO cases (
                        id, case_number, clinic_id, created_by_user_id,
                        responsible_dentist_user_id, status
                    )
                    VALUES (
                        :case_id, :case_number, :clinic_id, :user_id, :user_id, 'draft'
                    )
                    """
                ),
                {
                    "case_id": case_id,
                    "case_number": f"IMM-{uuid4().hex[:12]}",
                    "clinic_id": clinic_id,
                    "user_id": user_id,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO case_status_history (
                        id, case_id, to_status, action, actor_user_id
                    )
                    VALUES (:history_id, :case_id, 'draft', 'create', :user_id)
                    """
                ),
                {"history_id": history_id, "case_id": case_id, "user_id": user_id},
            )

            with pytest.raises(DBAPIError, match="değiştirilemez veya silinemez"):
                connection.execute(text(mutation), {"history_id": history_id})
        finally:
            transaction.rollback()
