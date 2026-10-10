from uuid import uuid4

from app.core.config import get_settings
from app.models import EmailOutbox
from app.services.email_dispatch import _build_email


def test_outbox_message_id_is_stable_across_retries() -> None:
    item_id = uuid4()
    item = EmailOutbox(
        id=item_id,
        recipient_user_id=uuid4(),
        recipient_email="recipient@example.test",
        subject="DentFlow test",
        body_text="Test",
        body_html="<p>Test</p>",
    )

    first = _build_email(item, get_settings())
    second = _build_email(item, get_settings())

    assert first["Message-ID"] == second["Message-ID"]
    assert first["X-DentFlow-Outbox-ID"] == str(item_id)
