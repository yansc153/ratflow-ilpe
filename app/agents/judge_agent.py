from typing import Dict, Any, List
from app.agents.base import BaseAgent
from app.harness.evidence_pipeline import format_validated_summary
from app.services.deepseek_client import deepseek
from app.config import settings

JUDGE_SYSTEM_PROMPT = """You are the final judge of an unusual options investigation case.

You must combine deterministic option features, public evidence, negative evidence, noise risk, and calibration data.

You must output:
- leakage_score
- tradeability_score
- model_estimated_profit_probability
- calibration_confidence
- calibration_grade
- event probabilities summing to 100
- main thesis
- risks
- data quality notes

Do not claim certainty.
Do not claim confirmed insider trading.
Do not recommend illegal behavior.

Separate event probability from tradeability.
If evidence is weak, say weak.
If data is missing, downgrade confidence."""


class JudgeAgent(BaseAgent):
    agent_name = "judge_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            dna = case_data.get("options_dna", {})
            merged = case_data.get("merged_evidence", {})
            hypothesis = case_data.get("event_hypothesis", {})
            noise = case_data.get("noise_agent", {})
            calibration_data = case_data.get("calibration_data", {})
            validated = case_data.get("validated_evidence", {})

            user_prompt = f"""Fuse all evidence and output final judgment.

## Options DNA
Score: {dna.get('options_dna_score', 0)}/100
Direction: {dna.get('direction', 'unclear')}
Contract Quality: {dna.get('contract_quality', 'unknown')}
Key Findings: {dna.get('key_findings', [])}
Red Flags: {dna.get('red_flags', [])}

## Event Hypothesis Prior
Event Probabilities: {hypothesis.get('event_probabilities', {})}
Likely Horizon: {hypothesis.get('likely_horizon', 'unknown')}
Reasoning: {hypothesis.get('summary', '')}

## Research Evidence Summary
{self._summarize_agents(merged.get('agent_outputs', {}))}

## Validated Evidence Bundle
{format_validated_summary(validated)}

## Noise Assessment
Noise Score: {noise.get('noise_score', 'N/A')}
Crowding: {noise.get('crowding_level', 'unknown')}
Red Flags: {noise.get('red_flags', [])}

## Calibration Context
Comparable cases: {calibration_data.get('comparable_count', 0)}
Calibration grade: {calibration_data.get('calibration_grade', 'uncalibrated')}

Output JSON:
{{
  "leakage_score": 0-100,
  "tradeability_score": 0-100,
  "model_estimated_profit_probability": 0.0-0.78,
  "calibration_confidence": "low|medium|high",
  "calibration_grade": "uncalibrated|early|calibrating|calibrated",
  "event_probabilities": {{
    "AI Transformation": <sum to 100>,
    "M&A / Strategic Transaction": <...>,
    "Major Contract / Government Order": <...>,
    "Earnings Surprise": <...>,
    "Regulatory / Legal / Patent / FDA": <...>,
    "Financing / Dilution": <...>,
    "Retail / Meme Speculation": <...>,
    "Hedge / Gamma / Market Maker Noise": <...>,
    "Other": <...>
  }},
  "main_thesis": "string in Chinese",
  "why_suspicious": ["list in Chinese"],
  "why_now": ["list in Chinese"],
  "key_risks": ["list in Chinese"],
  "data_quality_notes": ["list"]
}}

Rules:
- Event probabilities MUST sum to 100.
- If comparable cases < 30: cap model_estimated_profit_probability at 64%, calibration_confidence = low.
- If comparable cases 30-100: cap at 70%, confidence = medium.
- Never output probability above 78%.
- Main thesis and reasons should be in Chinese.
- Be conservative. This is not confirmed insider trading."""

            result = await deepseek.chat(
                system_prompt=JUDGE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=settings.deepseek_reasoning_model,
            )

            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({
                "leakage_score": result.get("leakage_score", 0),
                "tradeability_score": result.get("tradeability_score", 0),
                "model_estimated_profit_probability": result.get("model_estimated_profit_probability", 0),
                "calibration_confidence": result.get("calibration_confidence", "low"),
                "calibration_grade": result.get("calibration_grade", "uncalibrated"),
                "event_probabilities": result.get("event_probabilities", {}),
                "main_thesis": result.get("main_thesis", ""),
                "why_suspicious": result.get("why_suspicious", []),
                "why_now": result.get("why_now", []),
                "key_risks": result.get("key_risks", []),
                "data_quality_notes": result.get("data_quality_notes", []),
                "summary": result.get("main_thesis", ""),
                "score": result.get("leakage_score", 0),
            })
            self.logger.info("judge_complete", leakage_score=output["leakage_score"])
            return output
        except Exception as e:
            self.logger.error("judge_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e), "leakage_score": 0}

    def _summarize_agents(self, agent_outputs: Dict[str, Any]) -> str:
        lines = []
        for name, output in agent_outputs.items():
            if isinstance(output, dict):
                score = output.get("score", "N/A")
                summary = output.get("summary", "No summary")[:150]
                lines.append(f"- {name}: score={score}, {summary}")
        return "\n".join(lines) if lines else "No agent outputs available"
