from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CaseAction,
    DeliveryConfirmation,
    DentalCase,
    ProductionCompletion,
    Shipment,
    User,
)
from app.schemas.fulfillment import DeliveryConfirmRequest, ShipmentCreateRequest
from app.services.case_management.exceptions import CaseConflictError
from app.services.case_management.operation_support import (
    apply_operation_transition,
    production_run_for_case,
    shipment_for_case,
)
from app.services.case_management.repository import load_case
from app.services.case_management.transitions import authorize_transition


def create_shipment(
    db: Session,
    *,
    case_id: UUID,
    payload: ShipmentCreateRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = authorize_transition(case, actor, CaseAction.SHIP, reason=None)
    run = production_run_for_case(
        db,
        case_id=case.id,
        production_run_id=payload.production_run_id,
    )
    completion = db.scalar(
        select(ProductionCompletion).where(ProductionCompletion.production_run_id == run.id)
    )
    if completion is None:
        raise CaseConflictError("case_production_completion_required")
    if db.scalar(select(Shipment.id).where(Shipment.production_run_id == run.id)) is not None:
        raise CaseConflictError("case_already_shipped")
    shipment = Shipment(
        production_run_id=run.id,
        destination_clinic_id=case.clinic_id,
        carrier=payload.carrier,
        tracking_number=payload.tracking_number,
        shipped_by_user_id=actor.id,
        notes=payload.notes,
    )
    try:
        db.add(shipment)
        db.flush()
        apply_operation_transition(
            db,
            case=case,
            actor=actor,
            action=CaseAction.SHIP,
            next_status=next_status,
            audit_action="case.shipped",
            reason=None,
            audit_after={
                "production_run_id": run.id,
                "shipment_id": shipment.id,
                "carrier": shipment.carrier,
                "tracking_number": shipment.tracking_number,
                "destination_clinic_id": case.clinic_id,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return load_case(db, case.id)


def confirm_delivery(
    db: Session,
    *,
    case_id: UUID,
    payload: DeliveryConfirmRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = authorize_transition(case, actor, CaseAction.CONFIRM_DELIVERY, reason=None)
    shipment = shipment_for_case(db, case_id=case.id, shipment_id=payload.shipment_id)
    if shipment.destination_clinic_id != case.clinic_id:
        raise CaseConflictError("case_shipment_destination_changed")
    existing = db.scalar(
        select(DeliveryConfirmation.id).where(
            DeliveryConfirmation.shipment_id == shipment.id
        )
    )
    if existing is not None:
        raise CaseConflictError("case_delivery_already_confirmed")
    confirmation = DeliveryConfirmation(
        shipment_id=shipment.id,
        received_by_user_id=actor.id,
        notes=payload.notes,
    )
    try:
        db.add(confirmation)
        db.flush()
        apply_operation_transition(
            db,
            case=case,
            actor=actor,
            action=CaseAction.CONFIRM_DELIVERY,
            next_status=next_status,
            audit_action="case.delivery_confirmed",
            reason=None,
            audit_after={
                "shipment_id": shipment.id,
                "delivery_confirmation_id": confirmation.id,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return load_case(db, case.id)
