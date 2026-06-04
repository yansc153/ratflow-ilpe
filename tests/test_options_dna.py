import pytest
from app.agents.options_dna_agent import OptionsDNAAgent


def test_options_dna_high_score():
    agent = OptionsDNAAgent()
    result = agent._score({}, {
        "volume": 10000,
        "open_interest": 1000,
        "volume_oi_ratio": 10.0,
        "dte": 45,
        "otm_pct": 20.0,
        "iv_change": 0.10,
        "underlying_move_5d": 0.02,
        "bid": 0.45,
        "ask": 0.50,
        "mid_price": 0.475,
        "direction": "bullish",
    })
    assert result["options_dna_score"] >= 50
    assert result["dna_route"] == "FULL_RESEARCH"
    assert result["contract_quality"] in ("excellent", "good", "mixed", "poor")


def test_options_dna_low_score():
    agent = OptionsDNAAgent()
    result = agent._score({}, {
        "volume": 100,
        "open_interest": 500,
        "volume_oi_ratio": 0.2,
        "dte": 1,
        "otm_pct": 150.0,
        "iv_change": 1.0,
        "underlying_move_5d": 0.30,
        "bid": 0.05,
        "ask": 0.20,
        "mid_price": 0.125,
        "direction": "unclear",
    })
    assert result["options_dna_score"] < 40
    assert result["dna_route"] == "DROP_NOISE"


def test_options_dna_borderline_case_is_not_auto_rejected():
    agent = OptionsDNAAgent()
    result = agent._score({}, {
        "volume": 3000,
        "open_interest": 1300,
        "volume_oi_ratio": 2.3,
        "dte": 21,
        "otm_pct": 62.0,
        "iv_change": 0.04,
        "underlying_move_5d": 0.08,
        "bid": 1.2,
        "ask": 1.4,
        "mid_price": 1.3,
        "premium": 390000,
        "direction": "bullish",
    })
    assert result["options_dna_score"] >= 40
    assert result["dna_route"] in ("FULL_RESEARCH", "SPECULATIVE_RESEARCH")
    assert result["research_priority"] in ("light", "full", "urgent")


def test_options_dna_short_dated_high_convexity_routes_to_speculative():
    agent = OptionsDNAAgent()
    result = agent._score({}, {
        "volume": 5000,
        "open_interest": 300,
        "volume_oi_ratio": 16.6,
        "dte": 5,
        "otm_pct": 120.0,
        "iv_change": 0.04,
        "underlying_move_5d": 0.02,
        "bid": 0.9,
        "ask": 1.05,
        "mid_price": 0.975,
        "premium": 450000,
        "direction": "bullish",
    })
    assert result["convexity_score"] >= 45
    assert result["anomaly_score"] >= 45
    assert result["dna_route"] in ("SPECULATIVE_RESEARCH", "FULL_RESEARCH")


def test_options_dna_zero_dte_noise_stays_blocked():
    agent = OptionsDNAAgent()
    result = agent._score({}, {
        "volume": 80,
        "open_interest": 20,
        "volume_oi_ratio": 4.0,
        "dte": 0,
        "otm_pct": 90.0,
        "iv_change": 0.02,
        "underlying_move_5d": 0.18,
        "bid": 0.04,
        "ask": 0.18,
        "mid_price": 0.11,
        "premium": 8800,
        "direction": "bullish",
    })
    assert result["dna_route"] == "DROP_NOISE"


def test_options_dna_clamped():
    agent = OptionsDNAAgent()
    result = agent._score({}, {
        "volume": 1000000,
        "open_interest": 100,
        "volume_oi_ratio": 10000,
        "dte": 60,
        "otm_pct": 25.0,
        "iv_change": 0.15,
        "underlying_move_5d": 0.01,
        "bid": 1.0,
        "ask": 1.05,
        "mid_price": 1.025,
        "direction": "bullish",
    })
    assert 0 <= result["options_dna_score"] <= 100
