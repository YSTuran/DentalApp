from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DeliveryConfirmation,
    ProductionCompletion,
    ProductionRun,
    ReturnDecision,
    ReturnReceipt,
    Shipment,
    User,
)
from app.schemas.fulfillment import CaseOperationsResponse
from app.services.case_management.access import require_case_visibility
from app.services.case_management.repository import load_case


def get_case_operations(
    db: Session,
    *,
    case_id: UUID,
    actor: User,
) -> CaseOperationsResponse:
    case = load_case(db, case_id)
    require_case_visibility(actor, case)
    runs = list(
        db.scalars(
            select(ProductionRun)
            .where(ProductionRun.case_id == case_id)
            .order_by(ProductionRun.attempt_number)
        ).all()
    )
    run_ids = [run.id for run in runs]
    if not run_ids:
        return CaseOperationsResponse(
            production_runs=[],
            production_completions=[],
            shipments=[],
            delivery_confirmations=[],
            return_receipts=[],
            return_decisions=[],
        )

    completions = list(
        db.scalars(
            select(ProductionCompletion).where(
                ProductionCompletion.production_run_id.in_(run_ids)
            )
        ).all()
    )
    shipments = list(
        db.scalars(select(Shipment).where(Shipment.production_run_id.in_(run_ids))).all()
    )
    shipment_ids = [shipment.id for shipment in shipments]
    deliveries = []
    returns = []
    if shipment_ids:
        deliveries = list(
            db.scalars(
                select(DeliveryConfirmation).where(
                    DeliveryConfirmation.shipment_id.in_(shipment_ids)
                )
            ).all()
        )
        returns = list(
            db.scalars(
                select(ReturnReceipt).where(ReturnReceipt.shipment_id.in_(shipment_ids))
            ).all()
        )
    return_ids = [item.id for item in returns]
    decisions = (
        list(
            db.scalars(
                select(ReturnDecision).where(ReturnDecision.return_receipt_id.in_(return_ids))
            ).all()
        )
        if return_ids
        else []
    )
    return CaseOperationsResponse(
        production_runs=runs,
        production_completions=completions,
        shipments=shipments,
        delivery_confirmations=deliveries,
        return_receipts=returns,
        return_decisions=decisions,
    )
