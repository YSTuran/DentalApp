from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy import Sequence, func, select
from sqlalchemy.orm import Session

from app.models import (
    CaseAction,
    DentalCase,
    ProductionCompletion,
    ProductionRun,
    User,
)
from app.schemas.fulfillment import ProductionCompleteRequest, ProductionStartRequest
from app.services.case_management.exceptions import CaseConflictError
from app.services.case_management.operation_support import (
    apply_operation_transition,
    approved_design,
    production_run_for_case,
)
from app.services.case_management.repository import load_case
from app.services.case_management.transitions import authorize_transition

WORK_ORDER_SEQUENCE = Sequence("production_work_order_seq")


def _next_work_order_number(db: Session) -> str:
    value = db.scalar(select(WORK_ORDER_SEQUENCE.next_value()))
    if value is None:
        raise RuntimeError("İş emri numarası üretilemedi.")
    return f"ISE-{datetime.now(UTC).year}-{value:06d}"


def start_production(
    db: Session,
    *,
    case_id: UUID,
    payload: ProductionStartRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = authorize_transition(case, actor, CaseAction.START_PRODUCTION, reason=None)
    design = approved_design(case, expected_id=payload.design_file_version_id)
    latest_attempt = db.scalar(
        select(func.max(ProductionRun.attempt_number)).where(ProductionRun.case_id == case.id)
    )
    run = ProductionRun(
        case_id=case.id,
        attempt_number=(latest_attempt or 0) + 1,
        design_file_version_id=design.id,
        work_order_number=_next_work_order_number(db),
        started_by_user_id=actor.id,
        notes=payload.notes,
    )
    try:
        db.add(run)
        db.flush()
        apply_operation_transition(
            db,
            case=case,
            actor=actor,
            action=CaseAction.START_PRODUCTION,
            next_status=next_status,
            audit_action="case.production_started",
            reason=None,
            audit_after={
                "production_run_id": run.id,
                "attempt_number": run.attempt_number,
                "work_order_number": run.work_order_number,
                "design_file_version_id": design.id,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return load_case(db, case.id)


def complete_production(
    db: Session,
    *,
    case_id: UUID,
    payload: ProductionCompleteRequest,
    actor: User,
    request: Request,
) -> DentalCase:
    case = load_case(db, case_id, for_update=True)
    next_status = authorize_transition(case, actor, CaseAction.COMPLETE_PRODUCTION, reason=None)
    run = production_run_for_case(
        db,
        case_id=case.id,
        production_run_id=payload.production_run_id,
    )
    existing = db.scalar(
        select(ProductionCompletion.id).where(
            ProductionCompletion.production_run_id == run.id
        )
    )
    if existing is not None:
        raise CaseConflictError("case_production_already_completed")
    completion = ProductionCompletion(
        production_run_id=run.id,
        material=payload.material,
        lot_number=payload.lot_number,
        quantity=payload.quantity,
        completed_by_user_id=actor.id,
        notes=payload.notes,
    )
    try:
        db.add(completion)
        db.flush()
        apply_operation_transition(
            db,
            case=case,
            actor=actor,
            action=CaseAction.COMPLETE_PRODUCTION,
            next_status=next_status,
            audit_action="case.production_completed",
            reason=None,
            audit_after={
                "production_run_id": run.id,
                "production_completion_id": completion.id,
                "material": completion.material,
                "lot_number": completion.lot_number,
                "quantity": completion.quantity,
            },
            request=request,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return load_case(db, case.id)
