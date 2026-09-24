from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models import AuditEvent, User


def _json_object(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    encoded = jsonable_encoder(dict(value))
    if not isinstance(encoded, dict):
        raise TypeError("Audit verisi bir JSON nesnesi olmalıdır.")
    return encoded


def record_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: UUID | str,
    actor: User | None = None,
    clinic_id: UUID | None = None,
    reason: str | None = None,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
    request: Request | None = None,
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor_user_id=actor.id if actor is not None else None,
        actor_email=actor.email if actor is not None else None,
        clinic_id=clinic_id,
        reason=reason,
        before_data=_json_object(before),
        after_data=_json_object(after),
        context_data=_json_object(context) or {},
        ip_address=request.client.host if request is not None and request.client else None,
        user_agent=request.headers.get("user-agent") if request is not None else None,
    )
    db.add(event)
    db.flush()
    return event
