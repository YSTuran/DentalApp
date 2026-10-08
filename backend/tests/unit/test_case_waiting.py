from unittest.mock import Mock

from sqlalchemy.orm import Session

from app.services.case_waiting import create_overdue_case_alerts


def test_wait_alert_job_stops_when_another_scheduler_holds_the_lock() -> None:
    db = Mock(spec=Session)
    db.scalar.return_value = False

    assert create_overdue_case_alerts(db) == 0
    db.scalars.assert_not_called()
    db.commit.assert_not_called()
