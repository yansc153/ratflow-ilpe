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
