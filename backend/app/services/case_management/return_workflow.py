from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CaseAction,
    CaseFileKind,
    DeliveryConfirmation,
    DentalCase,
    ReturnDecision,
    ReturnReceipt,
    ReturnResolution,
    User,
)
from app.schemas.fulfillment import ReturnDecisionRequest, ReturnReceiptCreateRequest
from app.services.case_management.exceptions import CaseConflictError
from app.services.case_management.operation_support import (
    apply_operation_transition,
    shipment_for_case,
)
from app.services.case_management.repository import load_case
from app.services.case_management.reproduction import create_reproduction_case
from app.services.case_management.transitions import authorize_transition

RETURN_ACTIONS = {
    ReturnResolution.REPRODUCTION: CaseAction.DECIDE_REPRODUCTION,
    ReturnResolution.RESCAN: CaseAction.DECIDE_RESCAN,
}


def register_return_receipt(
    db: Session,
    *,
    case_id: UUID,
    payload: ReturnReceiptCreateRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = authorize_transition(
        case,
        actor,
        CaseAction.REGISTER_RETURN_RECEIVED,
        reason=payload.reason,
    )
    shipment = shipment_for_case(db, case_id=case.id, shipment_id=payload.shipment_id)
    delivery = db.scalar(
        select(DeliveryConfirmation).where(DeliveryConfirmation.shipment_id == shipment.id)
    )
    if delivery is None:
        raise CaseConflictError("case_delivery_confirmation_required")
    if db.scalar(
        select(ReturnReceipt.id).where(ReturnReceipt.shipment_id == shipment.id)
    ) is not None:
        raise CaseConflictError("case_return_already_received")
    receipt = ReturnReceipt(
        shipment_id=shipment.id,
        reason_code=payload.reason_code,
        reason=payload.reason,
        inspection_notes=payload.inspection_notes,
        received_by_user_id=actor.id,
    )
    try:
        db.add(receipt)
        db.flush()
        apply_operation_transition(
            db,
            case=case,
            actor=actor,
            action=CaseAction.REGISTER_RETURN_RECEIVED,
            next_status=next_status,
            audit_action="case.return_received",
            reason=payload.reason,
            audit_after={
                "shipment_id": shipment.id,
                "return_receipt_id": receipt.id,
                "reason_code": receipt.reason_code,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return load_case(db, case.id)


def decide_return(
    db: Session,
    *,
    case_id: UUID,
    payload: ReturnDecisionRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    action = RETURN_ACTIONS[payload.resolution]
    next_status = authorize_transition(case, actor, action, reason=payload.reason)
    receipt = db.get(ReturnReceipt, payload.return_receipt_id)
    if receipt is None:
        raise CaseConflictError("case_return_receipt_changed")
    shipment_for_case(db, case_id=case.id, shipment_id=receipt.shipment_id)
    if db.scalar(
        select(ReturnDecision.id).where(ReturnDecision.return_receipt_id == receipt.id)
    ) is not None:
        raise CaseConflictError("case_return_already_decided")
    scans = [file for file in case.file_versions if file.kind == CaseFileKind.SCAN]
    if not scans:
        raise CaseConflictError("case_scan_required")
    source_scan = max(scans, key=lambda file: file.version_number)
    reproduction = (
        create_reproduction_case(
            db,
            source_case=case,
            actor=actor,
            reason=payload.reason,
            request=request,
        )
        if payload.resolution == ReturnResolution.REPRODUCTION
        else None
    )
    decision = ReturnDecision(
        return_receipt_id=receipt.id,
        source_scan_file_version_id=source_scan.id,
        reproduction_case_id=reproduction.id if reproduction else None,
        resolution=payload.resolution,
        reason=payload.reason,
        decided_by_user_id=actor.id,
    )
    try:
        db.add(decision)
        db.flush()
        apply_operation_transition(
            db,
            case=case,
            actor=actor,
            action=action,
            next_status=next_status,
            audit_action=(
                "case.reproduction_requested"
                if payload.resolution == ReturnResolution.REPRODUCTION
                else "case.rescan_requested"
            ),
            reason=payload.reason,
            audit_after={
                "return_receipt_id": receipt.id,
                "return_decision_id": decision.id,
                "resolution": decision.resolution,
                "source_scan_file_version_id": source_scan.id,
                "reproduction_case_id": reproduction.id if reproduction else None,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return load_case(db, reproduction.id if reproduction else case.id)
