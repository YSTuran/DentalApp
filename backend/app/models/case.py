from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    CaseApprovalType,
    CaseDecision,
    CaseFileKind,
    CaseStatus,
    MeshValidationStatus,
)

CASE_STATUS_ENUM = Enum(
    CaseStatus,
    name="case_status",
    values_callable=lambda enum: [item.value for item in enum],
)
CASE_FILE_KIND_ENUM = Enum(
    CaseFileKind,
    name="case_file_kind",
    values_callable=lambda enum: [item.value for item in enum],
)
MESH_STATUS_ENUM = Enum(
    MeshValidationStatus,
    name="mesh_validation_status",
    values_callable=lambda enum: [item.value for item in enum],
)
CASE_APPROVAL_TYPE_ENUM = Enum(
    CaseApprovalType,
    name="case_approval_type",
    values_callable=lambda enum: [item.value for item in enum],
)
CASE_DECISION_ENUM = Enum(
    CaseDecision,
    name="case_decision",
    values_callable=lambda enum: [item.value for item in enum],
)


class DentalCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cases"

    case_number: Mapped[str] = mapped_column(String(32), nullable=False)
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    responsible_dentist_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    patient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[CaseStatus] = mapped_column(
        CASE_STATUS_ENUM,
        nullable=False,
        default=CaseStatus.DRAFT,
        server_default=CaseStatus.DRAFT.value,
        index=True,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    clinic = relationship("Clinic")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    responsible_dentist = relationship("User", foreign_keys=[responsible_dentist_user_id])
    details: Mapped["CaseDetail"] = relationship(
        back_populates="case",
        uselist=False,
    )
    file_versions: Mapped[list["CaseFileVersion"]] = relationship(
        back_populates="case",
        order_by="CaseFileVersion.created_at",
    )
    approvals: Mapped[list["CaseApproval"]] = relationship(
        back_populates="case",
        order_by="CaseApproval.created_at",
    )
    status_history: Mapped[list["CaseStatusHistory"]] = relationship(
        back_populates="case",
        order_by="CaseStatusHistory.created_at",
    )

    __table_args__ = (
        Index("uq_cases_case_number", "case_number", unique=True),
        Index("ix_cases_clinic_status", "clinic_id", "status"),
        Index("ix_cases_created_at", "created_at"),
    )


class CaseDetail(TimestampMixin, Base):
    __tablename__ = "case_details"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), primary_key=True
    )
    appliance_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tooth_numbers: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    special_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_fields: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    case: Mapped[DentalCase] = relationship(back_populates="details")

    __table_args__ = (
        CheckConstraint("jsonb_typeof(tooth_numbers) = 'array'", name="tooth_numbers_array"),
        CheckConstraint("jsonb_typeof(extra_fields) = 'object'", name="extra_fields_object"),
    )


class CaseFileVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "case_file_versions"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    kind: Mapped[CaseFileKind] = mapped_column(CASE_FILE_KIND_ENUM, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mesh_status: Mapped[MeshValidationStatus] = mapped_column(
        MESH_STATUS_ENUM,
        nullable=False,
        default=MeshValidationStatus.PENDING,
        server_default=MeshValidationStatus.PENDING.value,
    )
    mesh_report: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    case: Mapped[DentalCase] = relationship(back_populates="file_versions")
    uploaded_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("case_id", "kind", "version_number", name="uq_case_file_version_number"),
        UniqueConstraint("storage_key", name="uq_case_file_versions_storage_key"),
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
        Index("ix_case_file_versions_case_kind", "case_id", "kind"),
    )


class CaseApproval(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_approvals"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approval_type: Mapped[CaseApprovalType] = mapped_column(CASE_APPROVAL_TYPE_ENUM, nullable=False)
    decision: Mapped[CaseDecision] = mapped_column(CASE_DECISION_ENUM, nullable=False)
    file_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("case_file_versions.id", ondelete="RESTRICT"), nullable=False
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_self_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    case: Mapped[DentalCase] = relationship(back_populates="approvals")
    file_version = relationship("CaseFileVersion")
    actor = relationship("User")

    __table_args__ = (Index("ix_case_approvals_case_created", "case_id", "created_at"),)


class CaseStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_status_history"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    from_status: Mapped[CaseStatus | None] = mapped_column(CASE_STATUS_ENUM, nullable=True)
    to_status: Mapped[CaseStatus] = mapped_column(CASE_STATUS_ENUM, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    case: Mapped[DentalCase] = relationship(back_populates="status_history")
    actor = relationship("User")

    __table_args__ = (Index("ix_case_status_history_case_created", "case_id", "created_at"),)
