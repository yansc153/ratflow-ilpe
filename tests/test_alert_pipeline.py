import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, SessionLocal
from app.models import Base

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
