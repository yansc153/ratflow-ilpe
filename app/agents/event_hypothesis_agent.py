from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek


class EventHypothesisAgent(BaseAgent):
    agent_name = "event_hypothesis_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            contract = case_data.get("normalized_contract", {})
            dna = case_data.get("options_dna", {})

            user_prompt = f"""Analyze this unusual option alert and generate prior event probabilities.

Option Data:
- Ticker: {alert.get('ticker')}
- Type: {alert.get('option_type')}
- Strike: {alert.get('strike')}
- Expiry: {alert.get('expiry')}
- DTE: {contract.get('dte')}
- Volume/OI: {contract.get('volume')}/{contract.get('open_interest')}
- Premium: ${contract.get('premium', 0):,.0f}
- Underlying: ${contract.get('underlying_price')}
- OTM: {contract.get('otm_pct')}%
- Direction: {contract.get('direction')}
- IV Change: {contract.get('iv_change')}

Options DNA Score: {dna.get('options_dna_score', 0)}/100
Contract Quality: {dna.get('contract_quality', 'unknown')}

Based on option structure, DTE, volume/OI ratio, and direction, estimate what event categories are most likely being bet on.

Return JSON with event probabilities that sum to exactly 100:
{{
  "event_probabilities": {{
    "AI Transformation": <number>,
    "M&A / Strategic Transaction": <number>,
    "Major Contract / Government Order": <number>,
    "Earnings Surprise": <number>,
    "Regulatory / Legal / Patent / FDA": <number>,
    "Financing / Dilution": <number>,
    "Retail / Meme Speculation": <number>,
    "Hedge / Gamma / Market Maker Noise": <number>,
    "Other": <number>
  }},
  "likely_horizon": "short|medium|long",
  "reasoning": "string"
}}"""

            result = await deepseek.chat(
                system_prompt=AGENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output["event_probabilities"] = result.get("event_probabilities", {})
            output["likely_horizon"] = result.get("likely_horizon", "medium")
            output["summary"] = result.get("reasoning", "")
            output["score"] = 50
            return output
        except Exception as e:
            self.logger.error("event_hypothesis_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e), "event_probabilities": {}}
