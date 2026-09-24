from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.authorization import require_system_admin
from app.db.session import get_db
from app.models import AuditEvent, User
from app.schemas.audit import AuditEventListResponse

router = APIRouter()


@router.get("", response_model=AuditEventListResponse)
def list_audit_events(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_system_admin)],
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    actor_user_id: UUID | None = None,
    clinic_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditEventListResponse:
    filters = []
    if action is not None:
        filters.append(AuditEvent.action == action)
    if entity_type is not None:
        filters.append(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        filters.append(AuditEvent.entity_id == entity_id)
    if actor_user_id is not None:
        filters.append(AuditEvent.actor_user_id == actor_user_id)
    if clinic_id is not None:
        filters.append(AuditEvent.clinic_id == clinic_id)

    total = db.scalar(select(func.count()).select_from(AuditEvent).where(*filters)) or 0
    items = db.scalars(
        select(AuditEvent)
        .where(*filters)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return AuditEventListResponse(items=list(items), total=total, limit=limit, offset=offset)
