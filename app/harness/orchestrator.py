import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import logger
from app.models import (
    InvestigationCase, OptionAlert, AgentRun, EvidenceItem,
    LeakageReport, CaseStateTransition, Outcome,
)
from app.harness.state_machine import StateMachine
from app.harness.task_panel import TaskPanelManager
from app.harness.evidence_merger import EvidenceMerger
from app.harness.probability import ProbabilityEngine
from app.harness.calibration import CalibrationEngine

from app.agents.options_dna_agent import OptionsDNAAgent
from app.agents.event_hypothesis_agent import EventHypothesisAgent
from app.agents.sec_filings_agent import SECFilingsAgent
from app.agents.ai_transformation_agent import AITransformationAgent
from app.agents.ma_strategic_agent import MAStrategicAgent
from app.agents.major_contract_agent import MajorContractAgent
from app.agents.earnings_surprise_agent import EarningsSurpriseAgent
from app.agents.regulatory_legal_patent_agent import RegulatoryLegalPatentAgent
from app.agents.public_attention_noise_agent import PublicAttentionNoiseAgent
from app.agents.judge_agent import JudgeAgent
from app.agents.trade_construction_agent import TradeConstructionAgent

from app.services.options_contract_normalizer import normalizer
from app.services.report_renderer import report_renderer
from app.services.discord_bot_publisher import discord_publisher
from app.services.source_citation_service import citation_service


RESEARCH_AGENTS = [
    ("sec_filings_agent", SECFilingsAgent()),
    ("ai_transformation_agent", AITransformationAgent()),
    ("ma_strategic_agent", MAStrategicAgent()),
    ("major_contract_agent", MajorContractAgent()),
    ("earnings_surprise_agent", EarningsSurpriseAgent()),
    ("regulatory_legal_patent_agent", RegulatoryLegalPatentAgent()),
    ("public_attention_noise_agent", PublicAttentionNoiseAgent()),
]


class HarnessOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.task_manager = TaskPanelManager()

    async def run_case(self, case_id: int) -> Dict[str, Any]:
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        alert = self.db.query(OptionAlert).filter(OptionAlert.case_id == case_id).first()
        if not alert:
            raise ValueError(f"No alert for case {case_id}")

        logger.info("harness_start", case_uid=case.case_uid, ticker=alert.ticker)

        self._transition(case, "NORMALIZED", "Harness started")
        contract = normalizer.normalize(alert)
        case.direction = contract["direction"]
        case.main_contract_label = contract["contract_label"]
        self.db.commit()

        self._transition(case, "OPTION_DNA_SCORED", "Running Options DNA")
        dna_agent = OptionsDNAAgent()
        case_data = self._build_case_data(case, alert, contract)
        dna_result = await dna_agent.run(case_data)
        self._save_agent_run(case, alert, dna_agent.agent_name, case_data, dna_result)
        case_data["options_dna"] = dna_result

        dna_score = dna_result.get("options_dna_score", 0)
        if dna_score < settings.min_options_dna_research_score:
            self._transition(case, "LOW_PRIORITY", f"DNA score {dna_score} < threshold {settings.min_options_dna_research_score}")
            self.db.commit()
            logger.info("harness_low_priority", case_uid=case.case_uid, dna_score=dna_score)
            return {"status": "LOW_PRIORITY", "options_dna_score": dna_score}

        self._transition(case, "RESEARCH_RUNNING", f"DNA score {dna_score} >= threshold, launching research agents")

        parallel_tasks = [
            (name, lambda a=agent, d=case_data: a.run(d))
            for name, agent in RESEARCH_AGENTS
        ]
        research_results = await self.task_manager.run_parallel(parallel_tasks, timeout=settings.llm_timeout_seconds)

        for agent_name, result in research_results.items():
            self._save_agent_run(case, alert, agent_name, case_data, result)

        self._transition(case, "EVIDENCE_COLLECTED", "Research complete")
        noise_result = research_results.get("public_attention_noise_agent", {})

        merged = EvidenceMerger.merge(research_results, noise_result)
        case_data["merged_evidence"] = merged
        case_data["noise_agent"] = noise_result

        event_hypothesis_agent = EventHypothesisAgent()
        hypothesis_result = await event_hypothesis_agent.run(case_data)
        self._save_agent_run(case, alert, "event_hypothesis_agent", case_data, hypothesis_result)
        case_data["event_hypothesis"] = hypothesis_result

        self._transition(case, "JUDGED", "Running Judge Agent")
        judge = JudgeAgent()
        calibration_data = {"comparable_count": self._count_comparable(case), "calibration_grade": "uncalibrated"}
        case_data["calibration_data"] = calibration_data
        judge_result = await judge.run(case_data)
        self._save_agent_run(case, alert, "judge_agent", case_data, judge_result)
        case_data["judge_output"] = judge_result

        event_probs = ProbabilityEngine.validate_event_probabilities(judge_result.get("event_probabilities", {}))
        capped = ProbabilityEngine.cap_probability(
            judge_result.get("model_estimated_profit_probability", 0),
            calibration_data["comparable_count"],
        )

        self._transition(case, "TRADE_PLAN_READY", "Running Trade Construction Agent")
        trade_agent = TradeConstructionAgent()
        trade_result = await trade_agent.run(case_data)
        self._save_agent_run(case, alert, "trade_construction_agent", case_data, trade_result)

        leakage_score = judge_result.get("leakage_score", 0)
        tradeability_score = judge_result.get("tradeability_score", 0)

        report_ctx = self._build_report_context(case, alert, contract, dna_result, judge_result, trade_result, event_probs, capped)
        report_md = report_renderer.render_initial_report(report_ctx)

        report = LeakageReport(
            case_id=case.id,
            alert_id=alert.id,
            leakage_score=leakage_score,
            tradeability_score=tradeability_score,
            model_estimated_profit_probability=capped["probability"],
            calibration_confidence=capped["calibration_confidence"],
            calibration_grade=capped["calibration_grade"],
            event_probabilities_json=event_probs,
            option_dna_json=dna_result,
            research_evidence_json=merged,
            noise_risks_json=noise_result,
            trade_suggestion_json=trade_result,
            report_markdown=report_md,
        )
        self.db.add(report)
        self.db.commit()

        discord_sent = await self._publish_report(case, report, report_md, leakage_score)
        self.db.commit()

        logger.info("harness_complete", case_uid=case.case_uid, leakage_score=leakage_score)
        return {
            "status": "complete",
            "case_uid": case.case_uid,
            "leakage_score": leakage_score,
            "tradeability_score": tradeability_score,
            "discord_sent": discord_sent,
        }

    def _transition(self, case, to_status: str, reason: str = ""):
        from_status = case.status
        StateMachine.transition(case, to_status, reason)
        transition = CaseStateTransition(
            case_id=case.id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )
        self.db.add(transition)
        case.updated_at = datetime.utcnow()

    async def _publish_report(self, case, report, report_md: str, leakage_score: float) -> bool:
        if leakage_score < settings.min_discord_alert_score:
            logger.info("discord_skipped", case_uid=case.case_uid, score=leakage_score)
            self._transition(case, "PUBLISH_SKIPPED", f"Score {leakage_score} below Discord threshold {settings.min_discord_alert_score}")
            return False

        self._transition(case, "PUBLISH_PENDING", f"Discord send queued, score={leakage_score}")
        try:
            discord_result = await discord_publisher.send_long_message(report_md)
            if not discord_result:
                raise RuntimeError("Discord publisher returned no messages")
            report.discord_message_id = discord_result[0]["message_id"]
            self._transition(case, "PUBLISHED", f"Discord message sent, score={leakage_score}")
            self._transition(case, "OI_CONFIRMATION_PENDING", "Awaiting next-day OI confirmation")
            return True
        except Exception as e:
            logger.error("discord_send_failed", error=str(e))
            self._transition(case, "PUBLISH_RETRY_PENDING", f"Discord send failed: {str(e)[:100]}")
            return False

    def _build_case_data(self, case, alert, contract) -> Dict[str, Any]:
        return {
            "case_uid": case.case_uid,
            "case_id": case.id,
            "alert": {
                "ticker": alert.ticker,
                "company_name": alert.company_name,
                "option_type": alert.option_type,
                "strike": alert.strike,
                "expiry": alert.expiry,
                "dte": alert.dte,
                "volume": alert.volume,
                "open_interest": alert.open_interest,
                "bid": alert.bid,
                "ask": alert.ask,
                "last_price": alert.last_price,
                "implied_volatility": alert.implied_volatility,
                "iv_change": alert.iv_change,
                "premium": alert.premium,
                "underlying_price": alert.underlying_price,
                "underlying_move_5d": alert.underlying_move_5d,
                "raw_text": alert.raw_text,
                "source": alert.source,
            },
            "normalized_contract": contract,
            "options_dna": {},
        }

    def _save_agent_run(self, case, alert, agent_name: str, input_data: dict, output: dict):
        run = AgentRun(
            case_id=case.id,
            alert_id=alert.id,
            agent_name=agent_name,
            status="error" if "error" in output else "completed",
            input_json={"case_uid": case.case_uid},
            output_json=output,
            evidence_json=output if "evidence" not in agent_name else None,
            error=output.get("error"),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        self.db.add(run)

        for evidence_list_key in ["positive_evidence", "all_positive_evidence"]:
            for ev in output.get(evidence_list_key, []):
                if isinstance(ev, dict):
                    self.db.add(EvidenceItem(
                        case_id=case.id,
                        agent_name=agent_name,
                        evidence_type=ev.get("type", ""),
                        evidence_quality=ev.get("quality", "C"),
                        polarity="positive",
                        title=str(ev.get("title", ""))[:500],
                        source_name=str(ev.get("source_name", ""))[:200],
                        url=str(ev.get("url", ""))[:2000],
                        published_at=str(ev.get("date", "")),
                        snippet=str(ev.get("snippet", ""))[:2000],
                        relevance_score=float(ev.get("relevance", 0.5)),
                    ))

    def _count_comparable(self, case) -> int:
        try:
            return self.db.query(Outcome).count()
        except Exception:
            return 0

    def _build_report_context(self, case, alert, contract, dna, judge, trade, event_probs, capped) -> Dict[str, Any]:
        probs = event_probs or {}
        contract_original = trade.get("original_contract", {})

        return {
            "case_uid": case.case_uid,
            "ticker": alert.ticker,
            "direction_label": {"bullish": "看涨", "bearish": "看跌", "volatility": "波动率", "unclear": "不明确"}.get(contract.get("direction", "unclear"), "不明确"),
            "original_contract_label": contract.get("contract_label", ""),
            "bid": contract.get("bid", "N/A"),
            "ask": contract.get("ask", "N/A"),
            "mid": contract.get("mid_price", "N/A"),
            "last": contract.get("last_price", "N/A"),
            "iv": f"{contract.get('implied_volatility', 'N/A')}",
            "dte": contract.get("dte", "N/A"),
            "premium": f"{contract.get('premium', 0) or 0:,.0f}",
            "volume": contract.get("volume", 0),
            "open_interest": contract.get("open_interest", 0),
            "volume_oi_ratio": contract.get("volume_oi_ratio", "N/A"),
            "options_dna_score": dna.get("options_dna_score", 0),
            "contract_quality": dna.get("contract_quality", "unknown"),
            "leakage_score": judge.get("leakage_score", 0),
            "tradeability_score": judge.get("tradeability_score", 0),
            "profit_probability": round(capped.get("probability", 0) * 100, 1),
            "calibration_grade": capped.get("calibration_grade", "uncalibrated"),
            "calibration_confidence": capped.get("calibration_confidence", "low"),
            "p_ai": probs.get("AI Transformation", 0),
            "p_ma": probs.get("M&A / Strategic Transaction", 0),
            "p_contract": probs.get("Major Contract / Government Order", 0),
            "p_earnings": probs.get("Earnings Surprise", 0),
            "p_regulatory": probs.get("Regulatory / Legal / Patent / FDA", 0),
            "p_financing": probs.get("Financing / Dilution", 0),
            "p_noise": probs.get("Retail / Meme Speculation", 0) + probs.get("Hedge / Gamma / Market Maker Noise", 0),
            "p_other": probs.get("Other", 0),
            "why_suspicious": judge.get("why_suspicious", []),
            "positive_evidence": citation_service.format_evidence(judge.get("positive_evidence", []), "positive"),
            "negative_evidence": judge.get("key_risks", []) + (dna.get("red_flags", []) or []),
            "primary_action": trade.get("primary_action", "observe_only"),
            "original_contract_trade": contract_original.get("contract", ""),
            "alternative_contract_trade": (trade.get("alternative_contract", {}) or {}).get("contract", "无"),
            "position_size": contract_original.get("position_size", "0R"),
            "take_profit_plan": trade.get("take_profit_plan", []),
            "invalidation": trade.get("invalidation", []),
        }
