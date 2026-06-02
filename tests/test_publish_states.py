from types import SimpleNamespace

import pytest

import app.harness.orchestrator as orchestrator_module
from app.harness.orchestrator import HarnessOrchestrator


class FakeDB:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)


def make_orchestrator_case_report():
    orchestrator = HarnessOrchestrator(FakeDB())
    case = SimpleNamespace(id=1, case_uid="CASE123", status="TRADE_PLAN_READY", updated_at=None)
    report = SimpleNamespace(discord_message_id=None)
    return orchestrator, case, report


@pytest.mark.asyncio
async def test_publish_report_success_moves_to_oi_pending(monkeypatch):
    async def send_long_message(_report_md):
        return [{"message_id": "discord-1"}]

    monkeypatch.setattr(orchestrator_module.discord_publisher, "send_long_message", send_long_message)

    orchestrator, case, report = make_orchestrator_case_report()

    sent = await orchestrator._publish_report(case, report, "report", leakage_score=70)

    assert sent is True
    assert report.discord_message_id == "discord-1"
    assert case.status == "OI_CONFIRMATION_PENDING"


@pytest.mark.asyncio
async def test_publish_report_failure_waits_for_retry_without_oi(monkeypatch):
    async def send_long_message(_report_md):
        raise RuntimeError("discord down")

    monkeypatch.setattr(orchestrator_module.discord_publisher, "send_long_message", send_long_message)

    orchestrator, case, report = make_orchestrator_case_report()

    sent = await orchestrator._publish_report(case, report, "report", leakage_score=70)

    assert sent is False
    assert report.discord_message_id is None
    assert case.status == "PUBLISH_RETRY_PENDING"


@pytest.mark.asyncio
async def test_publish_report_low_score_is_skipped_without_oi(monkeypatch):
    async def send_long_message(_report_md):
        raise AssertionError("low-score reports must not call Discord")

    monkeypatch.setattr(orchestrator_module.discord_publisher, "send_long_message", send_long_message)

    orchestrator, case, report = make_orchestrator_case_report()

    sent = await orchestrator._publish_report(case, report, "report", leakage_score=10)

    assert sent is False
    assert report.discord_message_id is None
    assert case.status == "PUBLISH_SKIPPED"
