from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.models import InvestigationCase, Outcome
from app.schemas import OutcomeResponse, CalibrationStats
from app.harness.calibration import CalibrationEngine
from app.logging_config import logger

router = APIRouter(prefix="/outcomes", tags=["outcomes"])


@router.post("/update")
async def update_outcomes(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(_run_outcome_update)
    return {"status": "Outcome update started"}


@router.get("/stats/calibration", response_model=CalibrationStats)
async def calibration_stats(db: Session = Depends(get_db)):
    total = db.query(InvestigationCase).count()
    with_outcomes = db.query(Outcome).distinct(Outcome.case_id).count()

    grade_info = CalibrationEngine.calibration_grade(with_outcomes)

    return CalibrationStats(
        total_cases=total,
        cases_with_outcomes=with_outcomes,
        calibration_grade=grade_info["grade"],
        avg_leakage_score=None,
        avg_profit_probability=None,
    )


async def _run_outcome_update():
    db = SessionLocal()
    try:
        cases = db.query(InvestigationCase).filter(
            InvestigationCase.status.in_(["OI_CONFIRMED", "OI_REJECTED", "OI_INCONCLUSIVE", "OI_UNAVAILABLE", "OUTCOME_TRACKING"])
        ).all()

        horizons = ["1D", "3D", "7D", "14D", "30D", "expiry"]
        for case in cases:
            for horizon in horizons:
                existing = db.query(Outcome).filter(
                    Outcome.case_id == case.id,
                    Outcome.horizon == horizon,
                ).first()
                if not existing:
                    outcome = Outcome(
                        case_id=case.id,
                        alert_id=case.alert.id if case.alert else None,
                        horizon=horizon,
                        event_confirmed="pending",
                        checked_at=datetime.utcnow(),
                    )
                    db.add(outcome)

        db.commit()
        logger.info("outcome_update_done", cases=len(cases))
    except Exception as e:
        logger.error("outcome_update_failed", error=str(e))
    finally:
        db.close()
