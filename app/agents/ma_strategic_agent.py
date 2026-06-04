from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek


class MAStrategicAgent(BaseAgent):
    agent_name = "ma_strategic_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")
            company = alert.get("company_name", ticker)
            validated_ma = self.get_validated_bucket(case_data, "ma")
            sec_ctx = self.get_source_context(case_data, "sec_filings")
            search_ctx = self.get_source_context(case_data, "ma_search")

            user_prompt = f"""Research whether {company} ({ticker}) shows public clues of M&A, activist pressure, strategic review, asset sale, or restructuring.

Validated M&A evidence:
{self.render_validated_items(validated_ma)}

Retrieved SEC filing context:
{sec_ctx.get('data', []) if sec_ctx else []}

Retrieved public search context:
{search_ctx.get('data', []) if search_ctx else []}

Check for:
- 13D/13G filings showing activist or large stake accumulation
- Schedule TO for tender offers
- 8-K items related to M&A, board changes, asset sales
- Board composition changes (new directors with M&A background)
- CFO/CEO sudden departures
- Poison pill adoptions
- Asset sale announcements or divestiture programs
- Debt refinancing or restructuring
- "Strategic alternatives" language in filings or press releases
- Activist investor public letters or presentations
- Investment bank engagement announcements
- Privatization rumors from public sources
- Breakup or spin-off analysis from public sources

Return JSON:
{{
  "score": 0-100,
  "confidence": "low|medium|high",
  "summary": "string",
  "positive_evidence": [],
  "negative_evidence": [],
  "uncertainties": [],
  "errors": []
}}

Do not fabricate evidence. If unable to access data, state limitation clearly."""

            result = await deepseek.chat(system_prompt=AGENT_SYSTEM_PROMPT, user_prompt=user_prompt)
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({k: v for k, v in result.items() if k in output})
            output["retrieved_context"] = {
                "validated_bucket": validated_ma,
                "sec_filings": sec_ctx.get("data", []) if sec_ctx else [],
                "search": search_ctx.get("data", []) if search_ctx else [],
            }
            return output
        except Exception as e:
            self.logger.error("ma_strategic_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
