from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.routes_oi as routes_oi
from app.harness.orchestrator import HarnessOrchestrator
from app.models import Base, InvestigationCase, OptionAlert, OIConfirmation, Outcome


@pytest.fixture
def db_session_factory(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(routes_oi, "SessionLocal", testing_session)
    return testing_session


def create_pending_case(db):
    case = InvestigationCase(
        ticker="AAPL",
        company_name="Apple Inc.",
        source="test",
        status="OI_CONFIRMATION_PENDING",
    )
    db.add(case)
    db.flush()
    alert = OptionAlert(
        case_id=case.id,
        source="test",
        ticker="AAPL",
        option_type="CALL",
        strike=200.0,
        expiry="2026-08-15",
        dte=75,
        volume=5000,
        open_interest=2000,
        last_price=5.2,
        collected_at=datetime.utcnow(),
    )
    db.add(alert)
    db.commit()
    return case.id


@pytest.mark.asyncio
async def test_oi_confirmation_without_provider_marks_unavailable(db_session_factory):
    db = db_session_factory()
    case_id = create_pending_case(db)
    db.close()

    await routes_oi._run_oi_confirmation()

    db = db_session_factory()
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).one()
    confirmation = db.query(OIConfirmation).filter(OIConfirmation.case_id == case_id).one()

    assert case.status == "OI_UNAVAILABLE"
    assert confirmation.status == "OI_UNAVAILABLE"
    assert confirmation.new_oi is None
    assert confirmation.oi_change is None
    assert confirmation.oi_confirmation_ratio is None
    assert confirmation.score_delta == 0
    db.close()


def test_count_comparable_counts_outcomes(db_session_factory):
    db = db_session_factory()
    case_id = create_pending_case(db)
    alert = db.query(OptionAlert).filter(OptionAlert.case_id == case_id).one()
    db.add(Outcome(
        case_id=case_id,
        alert_id=alert.id,
        horizon="1D",
        event_confirmed="pending",
        checked_at=datetime.utcnow(),
    ))
    db.commit()

    orchestrator = HarnessOrchestrator(db)

    assert orchestrator._count_comparable(None) == 1
    db.close()
