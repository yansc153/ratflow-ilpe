import pytest

from app.agents.judge_agent import JudgeAgent


@pytest.mark.asyncio
async def test_judge_agent_includes_event_hypothesis_in_prompt(monkeypatch):
    captured = {}

    async def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "leakage_score": 55,
            "tradeability_score": 45,
            "model_estimated_profit_probability": 0.52,
            "calibration_confidence": "low",
            "calibration_grade": "uncalibrated",
            "event_probabilities": {"Major Contract / Government Order": 70, "Other": 30},
            "main_thesis": "测试结论",
            "why_suspicious": ["测试原因"],
            "why_now": ["测试时点"],
            "key_risks": ["测试风险"],
            "data_quality_notes": ["测试备注"],
        }

    monkeypatch.setattr("app.agents.judge_agent.deepseek.chat", fake_chat)

    agent = JudgeAgent()
    output = await agent.run(
        {
            "case_uid": "CASE123",
            "options_dna": {
                "options_dna_score": 42,
                "direction": "bullish",
                "contract_quality": "mixed",
                "key_findings": ["Volume/OI elevated"],
                "red_flags": [],
            },
            "merged_evidence": {"agent_outputs": {}},
            "event_hypothesis": {
                "event_probabilities": {"Major Contract / Government Order": 70, "Other": 30},
                "likely_horizon": "short",
                "summary": "Large call buying suggests contract-related speculation.",
            },
            "validated_evidence": {
                "missing_dimensions": ["missing_jobs"],
                "by_hypothesis": {
                    "contract": {
                        "count": 1,
                        "evidence": [
                            {
                                "reliability": "A",
                                "title": "8-K contract reference",
                                "source_name": "sec.gov",
                                "snippet": "Backlog expanded with defense customer",
                            }
                        ],
                    }
                },
            },
            "noise_agent": {"noise_score": 30, "crowding_level": "low", "red_flags": []},
            "calibration_data": {"comparable_count": 0, "calibration_grade": "uncalibrated"},
        }
    )

    assert output["leakage_score"] == 55
    assert "Major Contract / Government Order" in captured["user_prompt"]
    assert "Likely Horizon: short" in captured["user_prompt"]
    assert "Large call buying suggests contract-related speculation." in captured["user_prompt"]
    assert "8-K contract reference" in captured["user_prompt"]
    assert "Missing dimensions: ['missing_jobs']" in captured["user_prompt"]
