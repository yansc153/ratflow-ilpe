from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek


class AITransformationAgent(BaseAgent):
    agent_name = "ai_transformation_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")
            company = alert.get("company_name", ticker)

            user_prompt = f"""Research whether {company} ({ticker}) may be pivoting into AI or preparing AI-related announcements.

Check public sources:
- Company homepage and products page
- Investor relations page
- Recent press releases
- Job postings (AI, ML, LLM, data science, GPU, automation roles)
- GitHub repos if applicable
- Developer docs or API pages
- Partner announcements mentioning AI
- CEO/CFO language in earnings transcripts or interviews

Signals to detect:
- New AI product language appearing
- AI keyword frequency increasing over time
- Hiring for ML/LLM/data science/GPU/automation
- New AI partnerships announced
- New AI customer pages or case studies
- New AI developer docs or APIs
- Leadership language shifting toward AI

Return JSON:
{{
  "score": 0-100 (higher = stronger AI pivot evidence),
  "confidence": "low|medium|high",
  "summary": "string",
  "positive_evidence": [],
  "negative_evidence": [],
  "uncertainties": [],
  "errors": []
}}

If you cannot access actual data, return empty evidence with a note. Do not fabricate."""

            result = await deepseek.chat(system_prompt=AGENT_SYSTEM_PROMPT, user_prompt=user_prompt)
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({k: v for k, v in result.items() if k in output})
            return output
        except Exception as e:
            self.logger.error("ai_transformation_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
