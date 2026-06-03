from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek
from app.data_sources.news_search import NewsSearchAdapter
from app.data_sources.website_research import JobsResearchAdapter


class AITransformationAgent(BaseAgent):
    agent_name = "ai_transformation_agent"

    def __init__(self):
        super().__init__()
        self.search = NewsSearchAdapter()
        self.jobs = JobsResearchAdapter()

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")
            company = alert.get("company_name", ticker)
            site_ctx = await self.search.fetch(query=f'"{company}" AI product partnership investor relations careers', max_results=8)
            jobs_ctx = await self.jobs.fetch(company=company)

            user_prompt = f"""Research whether {company} ({ticker}) may be pivoting into AI or preparing AI-related announcements.

Retrieved public web context:
{site_ctx.get('data', [])}

Retrieved jobs context:
{jobs_ctx.get('data', [])}

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
            output["retrieved_context"] = {
                "web": site_ctx.get("data", []),
                "jobs": jobs_ctx.get("data", []),
            }
            return output
        except Exception as e:
            self.logger.error("ai_transformation_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
