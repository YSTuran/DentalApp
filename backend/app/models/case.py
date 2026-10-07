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
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    LargeBinary,
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
    UploadStatus,
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
UPLOAD_STATUS_ENUM = Enum(
    UploadStatus,
    name="upload_status",
    native_enum=False,
    create_constraint=True,
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
    patient_code_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    patient_code_lookup: Mapped[bytes | None] = mapped_column(LargeBinary(32), nullable=True)
    patient_name_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
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
    upload_sessions: Mapped[list["CaseUploadSession"]] = relationship(
        back_populates="case",
        order_by="CaseUploadSession.created_at",
    )
    approvals: Mapped[list["CaseApproval"]] = relationship(
        back_populates="case",
        order_by="CaseApproval.sequence_number",
    )
    status_history: Mapped[list["CaseStatusHistory"]] = relationship(
        back_populates="case",
        order_by="CaseStatusHistory.sequence_number",
    )

    __table_args__ = (
        Index("uq_cases_case_number", "case_number", unique=True),
        Index("ix_cases_clinic_status", "clinic_id", "status"),
        Index("ix_cases_created_at", "created_at"),
        Index("ix_cases_patient_code_lookup", "patient_code_lookup"),
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
    mesh_validation_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    mesh_validation_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    mesh_validated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    case: Mapped[DentalCase] = relationship(back_populates="file_versions")
    uploaded_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("id", "case_id", name="uq_case_file_versions_id_case"),
        UniqueConstraint("case_id", "kind", "version_number", name="uq_case_file_version_number"),
        UniqueConstraint("storage_key", name="uq_case_file_versions_storage_key"),
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
        CheckConstraint("length(sha256) = 64", name="sha256_length"),
        CheckConstraint(
            "mesh_validation_attempts >= 0",
            name="mesh_validation_attempts_non_negative",
        ),
        Index("ix_case_file_versions_case_kind", "case_id", "kind"),
    )


class CaseUploadSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "case_upload_sessions"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    kind: Mapped[CaseFileKind] = mapped_column(CASE_FILE_KIND_ENUM, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )
    expected_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    temp_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[UploadStatus] = mapped_column(
        UPLOAD_STATUS_ENUM,
        nullable=False,
        default=UploadStatus.PENDING,
        server_default=UploadStatus.PENDING.value,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    completed_file_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "case_file_versions.id",
            name="fk_upload_completed_file_version",
            ondelete="RESTRICT",
        ),
        nullable=True,
        unique=True,
    )

    case: Mapped[DentalCase] = relationship(back_populates="upload_sessions")
    created_by = relationship("User")
    completed_file_version = relationship("CaseFileVersion")

    __table_args__ = (
        UniqueConstraint("temp_storage_key", name="uq_case_upload_sessions_temp_storage_key"),
        CheckConstraint("expected_size > 0", name="expected_size_positive"),
        CheckConstraint("received_size >= 0", name="received_size_non_negative"),
        CheckConstraint("received_size <= expected_size", name="received_size_not_excessive"),
        CheckConstraint(
            "expected_sha256 IS NULL OR length(expected_sha256) = 64",
            name="expected_sha256_length",
        ),
        Index("ix_case_upload_sessions_case_status", "case_id", "status"),
        Index("ix_case_upload_sessions_expires_at", "expires_at"),
    )


class CaseApproval(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_approvals"

    sequence_number: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        nullable=False,
    )
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approval_type: Mapped[CaseApprovalType] = mapped_column(CASE_APPROVAL_TYPE_ENUM, nullable=False)
    decision: Mapped[CaseDecision] = mapped_column(CASE_DECISION_ENUM, nullable=False)
    file_version_id: Mapped[UUID] = mapped_column(
        nullable=False
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
    file_version = relationship("CaseFileVersion", viewonly=True)
    actor = relationship("User")

    __table_args__ = (
        ForeignKeyConstraint(
            ["file_version_id", "case_id"],
            ["case_file_versions.id", "case_file_versions.case_id"],
            name="fk_case_approvals_file_version_case",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "case_id",
            "approval_type",
            "file_version_id",
            name="uq_case_approval_file_decision",
        ),
        CheckConstraint(
            "decision = 'approved' OR "
            "(reason IS NOT NULL AND length(btrim(reason)) >= 3)",
            name="decision_reason_required",
        ),
        CheckConstraint(
            "NOT is_self_approval OR approval_type = 'manager_scan'",
            name="self_approval_manager_only",
        ),
        Index("uq_case_approvals_sequence_number", "sequence_number", unique=True),
        Index("ix_case_approvals_case_created", "case_id", "created_at"),
    )


class CaseStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "case_status_history"

    sequence_number: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        nullable=False,
    )
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

    __table_args__ = (
        Index("uq_case_status_history_sequence_number", "sequence_number", unique=True),
        Index("ix_case_status_history_case_created", "case_id", "created_at"),
    )
