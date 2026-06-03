from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek
from app.data_sources.website_research import GovContractsResearchAdapter
from app.data_sources.news_search import NewsSearchAdapter
from app.data_sources.sec_edgar import SECEdgarAdapter


class MajorContractAgent(BaseAgent):
    agent_name = "major_contract_agent"

    def __init__(self):
        super().__init__()
        self.gov = GovContractsResearchAdapter()
        self.search = NewsSearchAdapter()
        self.edgar = SECEdgarAdapter()

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")
            company = alert.get("company_name", ticker)
            gov_ctx = await self.gov.fetch(company=company)
            search_ctx = await self.search.fetch(query=f'"{company}" contract award customer partnership backlog bookings', max_results=6)
            filings_ctx = await self.edgar.fetch(ticker=ticker, limit=6)

            user_prompt = f"""Research whether {company} ({ticker}) may have a major customer contract, government order, defense award, cloud/enterprise deal, healthcare procurement, or supplier agreement pending.

Retrieved government/public procurement context:
{gov_ctx.get('data', [])}

Retrieved search context:
{search_ctx.get('data', [])}

Retrieved SEC filing context:
{filings_ctx.get('data', [])}

Check for public clues:
- Government procurement records (SAM.gov, defense.gov, state procurement)
- Press releases about new customers or partnerships
- Customer pages showing new logos or enterprise clients
- Partner pages showing expanded relationships
- Job postings for delivery, implementation, federal sales, government relations roles
- Backlog or order language in recent SEC filings
- Supplier/customer announcements from related companies
- Industry trade publications about contract awards
- Conference presentations about pipeline or bookings
- Revenue concentration disclosures in 10-K

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

Do not fabricate evidence. State limitations clearly if unable to access data."""

            result = await deepseek.chat(system_prompt=AGENT_SYSTEM_PROMPT, user_prompt=user_prompt)
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({k: v for k, v in result.items() if k in output})
            output["retrieved_context"] = {
                "gov_contracts": gov_ctx.get("data", []),
                "search": search_ctx.get("data", []),
                "sec_filings": filings_ctx.get("data", []),
            }
            return output
        except Exception as e:
            self.logger.error("major_contract_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
