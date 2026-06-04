from app.services.scanner_service import ScanOrchestrator


def test_apply_filters_keeps_one_day_high_premium_anomaly():
    orchestrator = ScanOrchestrator()
    alerts = [
        {
            "ticker": "NOC",
            "volume": 5000,
            "open_interest": 300,
            "last_price": 5.0,
            "dte": 1,
        }
    ]

    filtered = orchestrator._apply_filters(alerts)

    assert len(filtered) == 1
    assert filtered[0]["_vol_oi"] >= 2.0


def test_apply_filters_rejects_zero_dte_even_if_premium_large():
    orchestrator = ScanOrchestrator()
    alerts = [
        {
            "ticker": "NOC",
            "volume": 5000,
            "open_interest": 300,
            "last_price": 5.0,
            "dte": 0,
        }
    ]

    filtered = orchestrator._apply_filters(alerts)

    assert filtered == []
