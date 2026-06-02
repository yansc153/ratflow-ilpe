from typing import Dict, Any, List
from app.logging_config import logger


class CalibrationEngine:
    @staticmethod
    def find_comparable(outcomes: List[Dict[str, Any]], current: Dict[str, Any]) -> List[Dict[str, Any]]:
        comparable = []
        option_type = current.get("option_type", "")
        dte = current.get("dte", 0)
        leakage_bucket = current.get("leakage_score", 0) // 10 * 10

        for outcome in outcomes:
            if outcome.get("option_type") == option_type:
                comparable.append(outcome)
            elif abs(outcome.get("dte", 0) - (dte or 0)) <= 30:
                comparable.append(outcome)

        comparable = comparable[:200]
        return comparable

    @staticmethod
    def compute_brier_from_outcomes(outcomes: List[Dict[str, Any]]) -> float:
        if not outcomes:
            return 0.0
        components = []
        for o in outcomes:
            prob = o.get("predicted_probability", 0) or 0
            actual = 1.0 if o.get("event_confirmed") == "yes" else 0.0
            components.append((prob - actual) ** 2)
        return round(sum(components) / len(components), 4)

    @staticmethod
    def calibration_grade(comparable_count: int, brier: float = None) -> Dict[str, Any]:
        if comparable_count < 10:
            return {"grade": "uncalibrated", "confidence": "low"}
        elif comparable_count < 30:
            return {"grade": "early", "confidence": "low"}
        elif comparable_count < 100:
            return {"grade": "calibrating", "confidence": "medium"}
        else:
            if brier is not None and brier < 0.15:
                return {"grade": "calibrated", "confidence": "high"}
            return {"grade": "calibrating", "confidence": "medium"}
