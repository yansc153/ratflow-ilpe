import pytest
from app.harness.state_machine import StateMachine


def test_valid_transitions():
    assert StateMachine.can_transition("NEW", "NORMALIZED") is True
    assert StateMachine.can_transition("NORMALIZED", "OPTION_DNA_SCORED") is True
    assert StateMachine.can_transition("OPTION_DNA_SCORED", "RESEARCH_RUNNING") is True
    assert StateMachine.can_transition("OPTION_DNA_SCORED", "LOW_PRIORITY") is True
    assert StateMachine.can_transition("RESEARCH_RUNNING", "EVIDENCE_COLLECTED") is True
    assert StateMachine.can_transition("EVIDENCE_COLLECTED", "JUDGED") is True
    assert StateMachine.can_transition("JUDGED", "TRADE_PLAN_READY") is True
    assert StateMachine.can_transition("TRADE_PLAN_READY", "PUBLISH_PENDING") is True
    assert StateMachine.can_transition("PUBLISH_PENDING", "PUBLISHED") is True
    assert StateMachine.can_transition("PUBLISH_PENDING", "PUBLISH_RETRY_PENDING") is True
    assert StateMachine.can_transition("PUBLISH_RETRY_PENDING", "PUBLISH_PENDING") is True
    assert StateMachine.can_transition("TRADE_PLAN_READY", "PUBLISH_SKIPPED") is True
    assert StateMachine.can_transition("PUBLISHED", "OI_CONFIRMATION_PENDING") is True
    assert StateMachine.can_transition("OI_CONFIRMATION_PENDING", "OI_CONFIRMED") is True
    assert StateMachine.can_transition("OI_CONFIRMATION_PENDING", "OI_UNAVAILABLE") is True
    assert StateMachine.can_transition("OI_CONFIRMED", "OUTCOME_TRACKING") is True
    assert StateMachine.can_transition("OI_UNAVAILABLE", "OUTCOME_TRACKING") is True
    assert StateMachine.can_transition("OUTCOME_TRACKING", "CLOSED") is True
    assert StateMachine.can_transition("TRADE_PLAN_READY", "DISCORD_SENT") is True
    assert StateMachine.can_transition("DISCORD_SENT", "OI_CONFIRMATION_PENDING") is True


def test_invalid_transitions():
    assert StateMachine.can_transition("NEW", "JUDGED") is False
    assert StateMachine.can_transition("CLOSED", "NEW") is False
    assert StateMachine.can_transition("LOW_PRIORITY", "PUBLISHED") is False
    assert StateMachine.can_transition("PUBLISH_SKIPPED", "OI_CONFIRMATION_PENDING") is False
    assert StateMachine.can_transition("PUBLISH_RETRY_PENDING", "OI_CONFIRMATION_PENDING") is False
