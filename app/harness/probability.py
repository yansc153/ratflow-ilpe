from typing import Dict, Any
from app.logging_config import logger


class ProbabilityEngine:
    @staticmethod
    def cap_probability(probability: float, comparable_count: int) -> Dict[str, Any]:
        if comparable_count < 30:
            capped = min(probability, 0.64)
            confidence = "low"
            grade = "uncalibrated" if comparable_count < 10 else "early"
        elif comparable_count < 100:
            capped = min(probability, 0.70)
            confidence = "medium"
            grade = "calibrating"
        else:
            capped = min(probability, 0.78)
            confidence = "high"
            grade = "calibrated"

        return {
            "probability": round(capped, 4),
            "original_probability": round(probability, 4),
            "calibration_confidence": confidence,
            "calibration_grade": grade,
            "comparable_count": comparable_count,
        }

    @staticmethod
    def validate_event_probabilities(probs: Dict[str, float]) -> Dict[str, float]:
        if not probs:
            return {
                "AI Transformation": 20, "M&A / Strategic Transaction": 20,
                "Major Contract / Government Order": 15, "Earnings Surprise": 15,
                "Regulatory / Legal / Patent / FDA": 5, "Financing / Dilution": 5,
                "Retail / Meme Speculation": 10, "Hedge / Gamma / Market Maker Noise": 5,
                "Other": 5,
            }
        total = sum(probs.values())
        if total == 0:
            return ProbabilityEngine.validate_event_probabilities({})
        return {k: round(v / total * 100, 1) for k, v in probs.items()}
