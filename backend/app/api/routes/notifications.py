from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_csrf
from app.db.session import get_db
from app.models import Notification, User
from app.schemas.notification import (
    NotificationDismissResponse,
    NotificationListResponse,
)
from app.services.audit import record_audit_event

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> NotificationListResponse:
    filters = (
        Notification.recipient_user_id == user.id,
        Notification.dismissed_at.is_(None),
    )
    total = db.scalar(select(func.count()).select_from(Notification).where(*filters)) or 0
    items = db.scalars(
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
    ).all()
    return NotificationListResponse(items=list(items), total=total)


@router.post("/{notification_id}/dismiss", response_model=NotificationDismissResponse)
def dismiss_notification(
    notification_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> NotificationDismissResponse:
    notification = db.scalar(
        select(Notification)
        .where(
            Notification.id == notification_id,
            Notification.recipient_user_id == user.id,
        )
        .with_for_update()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="notification_not_found")
    if notification.dismissed_at is None:
        notification.dismissed_at = datetime.now(UTC)
        record_audit_event(
            db,
            action="notification.dismissed",
            entity_type="notification",
            entity_id=notification.id,
            actor=user,
            context={"source": "api", "kind": notification.kind},
            request=request,
        )
        db.commit()
    return NotificationDismissResponse(status="dismissed")
