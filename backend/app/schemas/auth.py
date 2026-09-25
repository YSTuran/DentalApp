from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import RoleCode


class SessionRequest(BaseModel):
    id_token: str = Field(min_length=20)
    remember_me: bool = False


class CsrfResponse(BaseModel):
    csrf_token: str


class ClinicRoleResponse(BaseModel):
    clinic_id: UUID
    role: RoleCode


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    global_roles: list[RoleCode]
    clinic_roles: list[ClinicRoleResponse]


class LogoutResponse(BaseModel):
    status: str = "ok"
