import csv
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.models import InvestigationCase, OptionAlert
from app.schemas import OptionAlertInput, OptionAlertResponse, CaseResponse
from app.harness.orchestrator import HarnessOrchestrator
from app.logging_config import logger

router = APIRouter(prefix="/alerts", tags=["alerts"])


async def _run_harness(case_id: int):
    db = SessionLocal()
    try:
        orchestrator = HarnessOrchestrator(db)
        await orchestrator.run_case(case_id)
    except Exception as e:
        logger.error("harness_background_failed", case_id=case_id, error=str(e))
    finally:
        db.close()


@router.post("/options", response_model=CaseResponse)
async def create_option_alert(
    payload: OptionAlertInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    case = InvestigationCase(
        ticker=payload.ticker.upper(),
        company_name=payload.company_name or payload.ticker.upper(),
        source=payload.source,
        status="NEW",
    )
    db.add(case)
    db.flush()

    oi = payload.open_interest or 0
    volume = payload.volume or 0
    volume_oi_ratio = round(volume / oi, 2) if oi > 0 else None

    mid_price = None
    if payload.bid is not None and payload.ask is not None:
        mid_price = round((payload.bid + payload.ask) / 2, 2)

    alert = OptionAlert(
        case_id=case.id,
        source=payload.source,
        ticker=payload.ticker.upper(),
        company_name=payload.company_name,
        option_type=payload.option_type.upper(),
        strike=payload.strike,
        expiry=payload.expiry,
        dte=payload.dte,
        volume=payload.volume,
        open_interest=payload.open_interest,
        volume_oi_ratio=volume_oi_ratio,
        bid=payload.bid,
        ask=payload.ask,
        last_price=payload.last_price,
        mid_price=mid_price,
        implied_volatility=payload.implied_volatility,
        iv_change=payload.iv_change,
        premium=payload.premium,
        underlying_price=payload.underlying_price,
        underlying_move_5d=payload.underlying_move_5d,
        raw_text=payload.raw_text,
        collected_at=datetime.utcnow(),
    )
    db.add(alert)
    db.commit()
    db.refresh(case)

    logger.info("alert_created", case_uid=case.case_uid, ticker=case.ticker)

    background_tasks.add_task(_run_harness, case.id)

    return case


@router.post("/import-csv")
async def import_csv_alerts(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return {"status": "CSV import endpoint ready. Use scripts/import_csv_alerts.py"}
