from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db import get_db
from app.models import InvestigationCase, LeakageReport
from app.schemas import CaseResponse, CaseDetailResponse, ReportResponse

router = APIRouter(tags=["reports"])


@router.get("/cases", response_model=list[CaseResponse])
async def list_cases(
    status: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    q = db.query(InvestigationCase)
    if status:
        q = q.filter(InvestigationCase.status == status)
    if ticker:
        q = q.filter(InvestigationCase.ticker == ticker.upper())
    q = q.order_by(InvestigationCase.created_at.desc()).offset(offset).limit(limit)
    return q.all()


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Case not found")

    alert_data = None
    if case.alert:
        alert_data = {
            "id": case.alert.id,
            "case_id": case.alert.case_id,
            "source": case.alert.source,
            "ticker": case.alert.ticker,
            "option_type": case.alert.option_type,
            "strike": case.alert.strike,
            "expiry": case.alert.expiry,
            "dte": case.alert.dte,
            "volume": case.alert.volume,
            "open_interest": case.alert.open_interest,
            "volume_oi_ratio": case.alert.volume_oi_ratio,
            "implied_volatility": case.alert.implied_volatility,
            "premium": case.alert.premium,
            "created_at": case.alert.created_at,
        }

    report_data = None
    if case.leakage_report:
        report_data = {
            "leakage_score": case.leakage_report.leakage_score,
            "tradeability_score": case.leakage_report.tradeability_score,
            "model_estimated_profit_probability": case.leakage_report.model_estimated_profit_probability,
            "event_probabilities_json": case.leakage_report.event_probabilities_json,
            "discord_message_id": case.leakage_report.discord_message_id,
        }

    return CaseDetailResponse(
        id=case.id,
        case_uid=case.case_uid,
        status=case.status,
        ticker=case.ticker,
        company_name=case.company_name,
        direction=case.direction,
        main_contract_label=case.main_contract_label,
        source=case.source,
        research_depth=case.research_depth,
        created_at=case.created_at,
        updated_at=case.updated_at,
        alert=alert_data,
        leakage_report=report_data,
    )


@router.get("/reports/recent", response_model=list[ReportResponse])
async def recent_reports(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    reports = db.query(LeakageReport).order_by(LeakageReport.created_at.desc()).limit(limit).all()
    return reports


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(LeakageReport).filter(LeakageReport.id == report_id).first()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    return report
