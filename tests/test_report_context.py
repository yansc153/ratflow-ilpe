from types import SimpleNamespace

from app.harness.orchestrator import HarnessOrchestrator


class FakeDB:
    def add(self, _item):
        return None


def test_build_report_context_includes_validated_evidence_sections():
    orchestrator = HarnessOrchestrator(FakeDB())
    case = SimpleNamespace(case_uid="CASE123", agent_runs=[], leakage_report=None)
    alert = SimpleNamespace(ticker="NOC")
    contract = {
        "direction": "bullish",
        "contract_label": "NOC 500C",
        "bid": 1.0,
        "ask": 1.2,
        "mid_price": 1.1,
        "last_price": 1.15,
        "implied_volatility": 0.3,
        "dte": 21,
        "premium": 100000,
        "volume": 1000,
        "open_interest": 120,
        "volume_oi_ratio": 8.3,
    }
    dna = {"options_dna_score": 55, "contract_quality": "good", "red_flags": []}
    judge = {"leakage_score": 45, "tradeability_score": 40, "why_suspicious": [], "key_risks": []}
    trade = {"primary_action": "observe_only", "original_contract": {"contract": "NOC 500C", "position_size": "0.5R"}, "take_profit_plan": [], "invalidation": []}
    validated = {
        "summary": "contract:2 | noise:1",
        "missing_dimensions": ["missing_jobs"],
        "conflicts": ["public_noise_dominates_signal"],
        "by_hypothesis": {
            "contract": {
                "count": 2,
                "sources": ["sec.gov", "example.com"],
                "evidence": [{"title": "8-K backlog update"}, {"title": "Agency award note"}],
            },
            "noise": {
                "count": 1,
                "sources": ["reddit.com"],
                "evidence": [{"title": "Retail hype thread"}],
            },
        },
    }
    route = {"selected_agents": ["sec_filings_agent", "major_contract_agent", "public_attention_noise_agent"]}

    ctx = orchestrator._build_report_context(case, alert, contract, dna, judge, trade, {}, {"probability": 0.5, "calibration_grade": "low", "calibration_confidence": "low"}, validated, route)

    assert ctx["validated_summary"] == "contract:2 | noise:1"
    assert ctx["validated_missing_dimensions"] == ["missing_jobs"]
    assert ctx["validated_conflicts"] == ["public_noise_dominates_signal"]
    assert ctx["hypothesis_route"] == ["sec_filings_agent", "major_contract_agent", "public_attention_noise_agent"]
    assert ctx["hypothesis_buckets"][0]["topic"] == "contract"
