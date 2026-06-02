from typing import Dict, Any
from app.logging_config import logger

VALID_TRANSITIONS = {
    "NEW": ["NORMALIZED", "CLOSED"],
    "NORMALIZED": ["OPTION_DNA_SCORED", "CLOSED"],
    "OPTION_DNA_SCORED": ["LOW_PRIORITY", "RESEARCH_RUNNING", "CLOSED"],
    "LOW_PRIORITY": ["CLOSED", "RESEARCH_RUNNING"],
    "RESEARCH_RUNNING": ["EVIDENCE_COLLECTED", "CLOSED"],
    "EVIDENCE_COLLECTED": ["JUDGED", "CLOSED"],
    "JUDGED": ["TRADE_PLAN_READY", "CLOSED"],
    "TRADE_PLAN_READY": [
        "PUBLISH_PENDING",
        "PUBLISH_SKIPPED",
        "PUBLISH_FAILED",
        "PUBLISHED",
        "DISCORD_SENT",
        "CLOSED",
    ],
    "PUBLISH_PENDING": ["PUBLISHED", "PUBLISH_RETRY_PENDING", "PUBLISH_FAILED", "CLOSED"],
    "PUBLISH_RETRY_PENDING": ["PUBLISH_PENDING", "PUBLISH_FAILED", "CLOSED"],
    "PUBLISH_SKIPPED": ["CLOSED", "OI_UNAVAILABLE"],
    "PUBLISH_FAILED": ["PUBLISH_RETRY_PENDING", "CLOSED"],
    "PUBLISHED": ["OI_CONFIRMATION_PENDING", "OI_UNAVAILABLE", "OUTCOME_TRACKING", "CLOSED"],
    "DISCORD_SENT": ["OI_CONFIRMATION_PENDING", "CLOSED"],
    "OI_CONFIRMATION_PENDING": ["OI_CONFIRMED", "OI_REJECTED", "OI_INCONCLUSIVE", "OI_UNAVAILABLE", "CLOSED"],
    "OI_CONFIRMED": ["OUTCOME_TRACKING", "CLOSED"],
    "OI_REJECTED": ["OUTCOME_TRACKING", "CLOSED"],
    "OI_INCONCLUSIVE": ["OUTCOME_TRACKING", "CLOSED"],
    "OI_UNAVAILABLE": ["OUTCOME_TRACKING", "CLOSED"],
    "OUTCOME_TRACKING": ["CLOSED"],
    "CLOSED": [],
}


class StateMachine:
    @staticmethod
    def can_transition(from_status: str, to_status: str) -> bool:
        allowed = VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed

    @staticmethod
    def transition(case, to_status: str, reason: str = ""):
        from_status = case.status
        if not StateMachine.can_transition(from_status, to_status):
            logger.error("invalid_transition", from_status=from_status, to_status=to_status)
            raise ValueError(f"Invalid transition: {from_status} → {to_status}")
        case.status = to_status
        logger.info("state_transition", from_status=from_status, to_status=to_status, reason=reason)
        return from_status, to_status, reason
