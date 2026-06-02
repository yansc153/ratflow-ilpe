from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek


class SECFilingsAgent(BaseAgent):
    agent_name = "sec_filings_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")

            user_prompt = f"""You are researching SEC filings for {ticker}.

Look for recent public clues in SEC filings:
- Latest 8-K, 10-Q, 10-K filings
- S-1, S-3 registrations
- DEF 14A proxy statements
- 13D/13G beneficial ownership filings
- Form 4 insider transactions
- Schedule TO tender offers

Search for these signals:
- AI language drift in filings
- "Strategic alternatives" language
- Acquisition or divestiture language
- Asset sales
- Customer concentration changes
- Backlog growth or decline
- Financing risk or dilution risk
- Going concern warnings
- Board or executive changes
- Insider buying or selling patterns
- New risk factors added
- Revenue recognition changes
- Segment reporting changes

Note: You should use public search. If you cannot access these filings, state the limitation.
For {ticker}, search SEC EDGAR for recent filings and identify any unusual language or patterns.

Return JSON:
{{
  "score": 0-100,
  "confidence": "low|medium|high",
  "summary": "string describing findings",
  "positive_evidence": [{{"type": "string", "quality": "A|B|C|D", "title": "string", "source_name": "string", "url": "string", "date": "string", "snippet": "string", "relevance": 0.0-1.0}}],
  "negative_evidence": [],
  "uncertainties": [],
  "errors": []
}}

If you cannot access actual SEC data, return an empty evidence array with a note in uncertainties. Do not fabricate filings. Only return what you can verify from public sources."""

            result = await deepseek.chat(system_prompt=AGENT_SYSTEM_PROMPT, user_prompt=user_prompt)
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({k: v for k, v in result.items() if k in output})
            return output
        except Exception as e:
            self.logger.error("sec_filings_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
