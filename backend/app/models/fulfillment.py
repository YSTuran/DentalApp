from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import ReturnReasonCode, ReturnResolution

RETURN_REASON_ENUM = Enum(
    ReturnReasonCode,
    name="return_reason_code",
    values_callable=lambda enum: [item.value for item in enum],
)
RETURN_RESOLUTION_ENUM = Enum(
    ReturnResolution,
    name="return_resolution",
    values_callable=lambda enum: [item.value for item in enum],
)


class ProductionRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "production_runs"

    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    design_file_version_id: Mapped[UUID] = mapped_column(nullable=False)
    work_order_number: Mapped[str] = mapped_column(String(32), nullable=False)
    started_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("id", "case_id", name="uq_production_runs_id_case"),
        UniqueConstraint("case_id", "attempt_number", name="uq_production_run_attempt"),
        UniqueConstraint("work_order_number", name="uq_production_run_work_order"),
        ForeignKeyConstraint(
            ["design_file_version_id", "case_id"],
            ["case_file_versions.id", "case_file_versions.case_id"],
            name="fk_production_run_design_case",
            ondelete="RESTRICT",
        ),
        CheckConstraint("attempt_number > 0", name="attempt_number_positive"),
        Index("ix_production_runs_case_started", "case_id", "started_at"),
    )


class ProductionCompletion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "production_completions"

    production_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_runs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    material: Mapped[str] = mapped_column(String(200), nullable=False)
    lot_number: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(btrim(material)) > 0", name="material_required"),
        CheckConstraint("length(btrim(lot_number)) > 0", name="lot_number_required"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )


class Shipment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "shipments"

    production_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("production_runs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    destination_clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    carrier: Mapped[str] = mapped_column(String(120), nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(120), nullable=False)
    shipped_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("carrier", "tracking_number", name="uq_shipment_carrier_tracking"),
        CheckConstraint("length(btrim(carrier)) > 0", name="carrier_required"),
        CheckConstraint("length(btrim(tracking_number)) > 0", name="tracking_number_required"),
        Index("ix_shipments_destination_shipped", "destination_clinic_id", "shipped_at"),
    )


class DeliveryConfirmation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "delivery_confirmations"

    shipment_id: Mapped[UUID] = mapped_column(
        ForeignKey("shipments.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    received_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReturnReceipt(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "return_receipts"

    shipment_id: Mapped[UUID] = mapped_column(
        ForeignKey("shipments.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    reason_code: Mapped[ReturnReasonCode] = mapped_column(RETURN_REASON_ENUM, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    inspection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(btrim(reason)) >= 3", name="return_reason_required"),
    )


class ReturnDecision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "return_decisions"

    return_receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("return_receipts.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    source_scan_file_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("case_file_versions.id", ondelete="RESTRICT"), nullable=False
    )
    reproduction_case_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("cases.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    resolution: Mapped[ReturnResolution] = mapped_column(RETURN_RESOLUTION_ENUM, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("length(btrim(reason)) >= 3", name="return_decision_reason_required"),
        CheckConstraint(
            "(resolution = 'reproduction' AND reproduction_case_id IS NOT NULL) OR "
            "(resolution = 'rescan' AND reproduction_case_id IS NULL)",
            name="return_decision_reproduction_case",
        ),
    )
