from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek
from app.data_sources.market_context import YFinanceResearchAdapter
from app.data_sources.news_search import NewsSearchAdapter


class EarningsSurpriseAgent(BaseAgent):
    agent_name = "earnings_surprise_agent"

    def __init__(self):
        super().__init__()
        self.market = YFinanceResearchAdapter()
        self.search = NewsSearchAdapter()

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")
            company = alert.get("company_name", ticker)
            dte = case_data.get("normalized_contract", {}).get("dte", 0)
            validated_earnings = self.get_validated_bucket(case_data, "earnings")
            market_ctx = self.get_source_context(case_data, "market")
            search_ctx = self.get_source_context(case_data, "earnings_search")
            if not market_ctx:
                market_ctx = await self.market.fetch(ticker=ticker)
            if not search_ctx:
                search_ctx = await self.search.fetch(query=f"{ticker} earnings guidance analyst estimate revisions", max_results=6)

            user_prompt = f"""Research whether the unusual option activity for {company} ({ticker}) may be betting on an earnings surprise.

DTE: {dte} days to expiration.

Validated earnings evidence:
{self.render_validated_items(validated_earnings)}

Retrieved market context:
{market_ctx.get('data', {})}

Retrieved public search context:
{search_ctx.get('data', [])}

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
            output["retrieved_context"] = {
                "validated_bucket": validated_earnings,
                "market": market_ctx.get("data", {}),
                "search": search_ctx.get("data", []),
            }
            return output
        except Exception as e:
            self.logger.error("earnings_surprise_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
