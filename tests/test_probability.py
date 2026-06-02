import pytest
from app.harness.probability import ProbabilityEngine


def test_validate_event_probabilities_sums_to_100():
    probs = {
        "AI Transformation": 30,
        "M&A / Strategic Transaction": 20,
        "Major Contract / Government Order": 15,
        "Earnings Surprise": 15,
        "Regulatory / Legal / Patent / FDA": 5,
        "Financing / Dilution": 5,
        "Retail / Meme Speculation": 5,
        "Hedge / Gamma / Market Maker Noise": 3,
        "Other": 2,
    }
    result = ProbabilityEngine.validate_event_probabilities(probs)
    total = sum(result.values())
    assert abs(total - 100) < 0.5


def test_validate_empty_probs():
    result = ProbabilityEngine.validate_event_probabilities({})
    total = sum(result.values())
    assert abs(total - 100) < 0.5


def test_cap_probability_low_samples():
    result = ProbabilityEngine.cap_probability(0.85, comparable_count=5)
    assert result["probability"] <= 0.64
    assert result["calibration_confidence"] == "low"


def test_cap_probability_medium_samples():
    result = ProbabilityEngine.cap_probability(0.85, comparable_count=50)
    assert result["probability"] <= 0.70
    assert result["calibration_confidence"] == "medium"


def test_cap_probability_high_samples():
    result = ProbabilityEngine.cap_probability(0.70, comparable_count=150)
    assert result["probability"] <= 0.78
    assert result["calibration_confidence"] == "high"
