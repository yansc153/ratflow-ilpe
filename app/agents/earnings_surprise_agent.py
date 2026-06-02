from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek


class EarningsSurpriseAgent(BaseAgent):
    agent_name = "earnings_surprise_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")
            company = alert.get("company_name", ticker)
            dte = case_data.get("normalized_contract", {}).get("dte", 0)

            user_prompt = f"""Research whether the unusual option activity for {company} ({ticker}) may be betting on an earnings surprise.

DTE: {dte} days to expiration.

Check public clues:
- Next earnings date estimate
- Previous earnings guidance (raise, maintain, lower)
- Peer earnings results and sector trends
- Hiring growth acceleration or deceleration
- Customer momentum indicators (app downloads, website traffic if public)
- Margin/inventory/backlog commentary from recent filings
- Analyst estimate revisions where publicly available
- Insider trading patterns around earnings
- Historical earnings beat/miss pattern
- Pre-announcement patterns
- Short interest changes

Return JSON:
{{
  "score": 0-100,
  "confidence": "low|medium|high",
  "earnings_proximity": "pre_earnings|post_earnings|mid_cycle|unclear",
  "expected_direction": "beat|miss|inline|unclear",
  "summary": "string",
  "positive_evidence": [],
  "negative_evidence": [],
  "uncertainties": [],
  "errors": []
}}

Do not fabricate."""

            result = await deepseek.chat(system_prompt=AGENT_SYSTEM_PROMPT, user_prompt=user_prompt)
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({k: v for k, v in result.items() if k in output})
            return output
        except Exception as e:
            self.logger.error("earnings_surprise_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
