import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, SessionLocal
from app.harness.orchestrator import HarnessOrchestrator
from app.models import AgentRun, CaseStateTransition, EvidenceItem, InvestigationCase, OptionAlert

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def test_create_alert():
    payload = {
        "source": "test",
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "option_type": "CALL",
        "strike": 200.0,
        "expiry": "2026-08-15",
        "dte": 75,
        "volume": 5000,
        "open_interest": 2000,
        "bid": 5.0,
        "ask": 5.5,
        "last_price": 5.2,
        "implied_volatility": 0.30,
        "iv_change": 0.05,
        "premium": 2500000,
        "underlying_price": 185.0,
        "underlying_move_5d": 0.03,
        "raw_text": "Test alert",
    }
    response = client.post("/alerts/options", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["status"] in ("NEW", "NORMALIZED")
    assert "case_uid" in data


def test_get_cases():
    response = client.get("/cases")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_case_not_found():
    response = client.get("/cases/99999")
    assert response.status_code == 404


def test_get_case_includes_agent_runs_and_evidence_items():
    db = SessionLocal()
    try:
        case = InvestigationCase(ticker="NOC", status="PUBLISH_SKIPPED")
        db.add(case)
        db.flush()
        alert = OptionAlert(
            case_id=case.id,
            source="test",
            ticker="NOC",
            option_type="CALL",
            strike=450.0,
            expiry="2026-06-18",
            volume=70,
            open_interest=5,
        )
        db.add(alert)
        db.flush()
        db.add(
            AgentRun(
                case_id=case.id,
                alert_id=alert.id,
                agent_name="sec_filings_agent",
                status="completed",
                output_json={"score": 0, "summary": "Unable to access SEC filings"},
            )
        )
        db.add(
            EvidenceItem(
                case_id=case.id,
                agent_name="ma_strategic_agent",
                evidence_quality="C",
                polarity="positive",
                title="Strategic review reference",
                source_name="Northrop investor relations",
                url="https://example.com",
                snippet="Historic strategic review language",
                relevance_score=0.5,
            )
        )
        db.commit()

        response = client.get(f"/cases/{case.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_runs"][0]["agent_name"] == "sec_filings_agent"
        assert data["evidence_items"][0]["agent_name"] == "ma_strategic_agent"
    finally:
        db.close()


def test_save_agent_run_defaults_non_numeric_relevance():
    db = SessionLocal()
    try:
        case = InvestigationCase(ticker="NOC", status="NEW")
        db.add(case)
        db.flush()
        alert = OptionAlert(
            case_id=case.id,
            source="test",
            ticker="NOC",
            option_type="CALL",
            strike=500.0,
            expiry="2026-06-12",
            volume=1000,
            open_interest=100,
        )
        db.add(alert)
        db.flush()

        HarnessOrchestrator(db)._save_agent_run(
            case,
            alert,
            "major_contract_agent",
            {},
            {
                "positive_evidence": [
                    {
                        "title": "Contract clue",
                        "relevance": "Indicates significant existing orders and potential future contracts.",
                    }
                ]
            },
        )
        db.commit()

        assert db.query(AgentRun).filter_by(case_id=case.id).count() == 1
        evidence = db.query(EvidenceItem).filter_by(case_id=case.id).one()
        assert evidence.relevance_score == 0.5
    finally:
        db.close()


def test_transition_to_same_status_is_idempotent():
    db = SessionLocal()
    try:
        case = InvestigationCase(ticker="FCX", status="NORMALIZED")
        db.add(case)
        db.flush()

        HarnessOrchestrator(db)._transition(case, "NORMALIZED", "retry")
        db.commit()

        assert case.status == "NORMALIZED"
        assert db.query(CaseStateTransition).filter_by(case_id=case.id).count() == 0
    finally:
        db.close()
