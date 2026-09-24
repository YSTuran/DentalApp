from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: str
    entity_type: str
    entity_id: str
    actor_user_id: UUID | None
    actor_email: str | None
    clinic_id: UUID | None
    reason: str | None
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    context: dict[str, Any] = Field(validation_alias="context_data")
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int
