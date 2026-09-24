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
        "UPDATE audit_events SET action = 'changed' WHERE id = :id",
        "DELETE FROM audit_events WHERE id = :id",
        "TRUNCATE TABLE audit_events",
    ],
)
def test_audit_events_reject_every_mutation(mutation: str) -> None:
    event_id = uuid4()

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO audit_events (id, action, entity_type, entity_id)
                    VALUES (:id, 'test.created', 'test', :entity_id)
                    """
                ),
                {"id": event_id, "entity_id": str(event_id)},
            )

            with pytest.raises(DBAPIError, match="değiştirilemez veya silinemez"):
                connection.execute(text(mutation), {"id": event_id})
        finally:
            transaction.rollback()
