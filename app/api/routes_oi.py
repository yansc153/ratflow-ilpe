from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.models import InvestigationCase, OptionAlert, OIConfirmation, CaseStateTransition
from app.schemas import OIConfirmationResponse
from app.harness.state_machine import StateMachine
from app.logging_config import logger

router = APIRouter(prefix="/oi", tags=["oi"])


@router.post("/confirm")
async def run_oi_confirmation(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(_run_oi_confirmation)
    return {"status": "OI confirmation started"}


@router.get("/pending", response_model=list[OIConfirmationResponse])
async def pending_oi(db: Session = Depends(get_db)):
    cases = db.query(InvestigationCase).filter(
        InvestigationCase.status == "OI_CONFIRMATION_PENDING"
    ).all()
    results = []
    for case in cases:
        oi_records = db.query(OIConfirmation).filter(
            OIConfirmation.case_id == case.id
        ).order_by(OIConfirmation.checked_at.desc()).all()
        for r in oi_records:
            results.append(r)
    return results


async def _run_oi_confirmation():
    db = SessionLocal()
    try:
        cases = db.query(InvestigationCase).filter(
            InvestigationCase.status == "OI_CONFIRMATION_PENDING"
        ).all()

        for case in cases:
            alert = db.query(OptionAlert).filter(OptionAlert.case_id == case.id).first()
            if not alert:
                continue

            report = case.leakage_report
            old_score = report.leakage_score if report else 0

            confirmation = OIConfirmation(
                case_id=case.id,
                alert_id=alert.id,
                old_oi=alert.open_interest,
                new_oi=None,
                alert_day_volume=alert.volume,
                oi_change=None,
                oi_confirmation_ratio=None,
                status="OI_UNAVAILABLE",
                old_leakage_score=old_score,
                new_leakage_score=old_score,
                score_delta=0,
                checked_at=datetime.utcnow(),
            )
            db.add(confirmation)

            from_status = case.status
            StateMachine.transition(case, "OI_UNAVAILABLE", "No provider-backed OI snapshot is configured")
            db.add(CaseStateTransition(
                case_id=case.id,
                from_status=from_status,
                to_status="OI_UNAVAILABLE",
                reason="No provider-backed OI snapshot is configured",
            ))

            logger.info("oi_confirmation_unavailable", case_uid=case.case_uid)

        db.commit()
    except Exception as e:
        logger.error("oi_confirmation_failed", error=str(e))
    finally:
        db.close()
