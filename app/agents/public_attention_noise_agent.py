from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek
from app.data_sources.market_context import YFinanceResearchAdapter
from app.data_sources.news_search import NewsSearchAdapter
from app.data_sources.website_research import SocialResearchAdapter, PriceDataAdapter


class PublicAttentionNoiseAgent(BaseAgent):
    agent_name = "public_attention_noise_agent"

    def __init__(self):
        super().__init__()
        self.market = YFinanceResearchAdapter()
        self.news = NewsSearchAdapter()
        self.social = SocialResearchAdapter()
        self.price = PriceDataAdapter()

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")
            contract = case_data.get("normalized_contract", {})
            validated_noise = self.get_validated_bucket(case_data, "noise")
            market_ctx = self.get_source_context(case_data, "market")
            news_ctx = self.get_source_context(case_data, "noise_search")
            social_ctx = self.get_source_context(case_data, "social")
            price_ctx = self.get_source_context(case_data, "price")
            if not market_ctx:
                market_ctx = await self.market.fetch(ticker=ticker)
            if not news_ctx:
                news_ctx = await self.news.fetch(query=f"{ticker} stock news unusual options hype earnings", max_results=6)
            if not social_ctx:
                social_ctx = await self.social.fetch(ticker=ticker)
            if not price_ctx:
                price_ctx = await self.price.fetch(ticker=ticker)

            user_prompt = f"""Act as the cold-water agent for unusual option activity in {ticker}.

Validated noise evidence:
{self.render_validated_items(validated_noise)}

Retrieved market context:
{market_ctx.get('data', {})}

Retrieved news context:
{news_ctx.get('data', [])}

Retrieved social/search context:
{social_ctx.get('data', [])}

Retrieved price context:
{price_ctx.get('data', {})}

Determine whether the option flow is likely:
- Public hype / meme speculation
- Earnings gambling
- Hedge/gamma positioning noise
- Already priced in by public news

Check for noise indicators:
- Recent news volume and sentiment for {ticker}
- Social media chatter level (Reddit, Stocktwits, X)
- Recent stock price run-up before the option alert
- Proximity to earnings date
- IV level relative to historical (current IV: {contract.get('implied_volatility')})
- Bid/ask spread quality (bid: {contract.get('bid')}, ask: {contract.get('ask')})
- Meme stock characteristics
- Market cap and float characteristics

Return JSON:
{{
  "noise_score": 0-100 (higher = more likely noise, not signal),
  "crowding_level": "low|medium|high|extreme",
  "public_catalyst_explanation": "string describing any public news that already explains the flow",
  "red_flags": ["list of noise indicators found"],
  "score": 0-100,
  "confidence": "low|medium|high",
  "summary": "string",
  "positive_evidence": [],
  "negative_evidence": [],
  "uncertainties": [],
  "errors": []
}}

If you cannot access real-time social data, estimate based on company characteristics and note the limitation. Do not fabricate data."""

            result = await deepseek.chat(system_prompt=AGENT_SYSTEM_PROMPT, user_prompt=user_prompt)
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({k: v for k, v in result.items() if k in output})
            output["retrieved_context"] = {
                "validated_bucket": validated_noise,
                "market": market_ctx.get("data", {}),
                "news": news_ctx.get("data", []),
                "social": social_ctx.get("data", []),
                "price": price_ctx.get("data", {}),
            }
            return output
        except Exception as e:
            self.logger.error("public_attention_noise_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
