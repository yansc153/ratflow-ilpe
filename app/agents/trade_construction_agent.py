from typing import Dict, Any
from app.agents.base import BaseAgent
from app.services.deepseek_client import deepseek
from app.config import settings

TRADE_SYSTEM_PROMPT = """You are a trade construction agent for an unusual options investigation system.

You convert judged cases into practical option-following suggestions with clear original-contract guidance.

You never recommend illegal behavior.
You never guarantee profit.
You always include invalidation conditions.
Position sizing must be conservative.
Always show the original contract clearly.

IMPORTANT: Output ONLY valid JSON. No markdown, no explanation outside the JSON."""


class TradeConstructionAgent(BaseAgent):
    agent_name = "trade_construction_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            contract = case_data.get("normalized_contract", {})
            judge = case_data.get("judge_output", {})
            leakage = judge.get("leakage_score", 0)
            tradeability = judge.get("tradeability_score", 0)

            user_prompt = f"""Construct a trade suggestion based on this judged case.

## Original Contract
Ticker: {alert.get('ticker')}
Type: {alert.get('option_type')}
Strike: {alert.get('strike')}
Expiry: {alert.get('expiry')}
DTE: {contract.get('dte')}
Bid: {contract.get('bid')}
Ask: {contract.get('ask')}
Mid: {contract.get('mid_price')}
Last: {contract.get('last_price')}
IV: {contract.get('implied_volatility')}
Volume: {contract.get('volume')}
OI: {contract.get('open_interest')}

## Judgment
Leakage Score: {leakage}/100
Tradeability Score: {tradeability}/100
Model-Estimated Profit Probability: {judge.get('model_estimated_profit_probability', 0):.0%}
Main Thesis: {judge.get('main_thesis', '')}
Key Risks: {judge.get('key_risks', [])}

Output JSON:
{{
  "trade_bias": "bullish|bearish|neutral|avoid",
  "primary_action": "strong_follow|small_follow|observe_only|avoid",
  "original_contract": {{
    "contract": "Buy {alert.get('ticker')} {alert.get('expiry')} {alert.get('strike')}{'C' if alert.get('option_type') == 'CALL' else 'P'}",
    "option_type": "{alert.get('option_type')}",
    "strike": {alert.get('strike')},
    "expiry": "{alert.get('expiry')}",
    "action": "buy_to_open|observe|avoid",
    "follow_original_flow": true,
    "bid": {contract.get('bid') or 0},
    "ask": {contract.get('ask') or 0},
    "mid": {contract.get('mid_price') or 0},
    "last": {contract.get('last_price') or 0},
    "implied_volatility": {contract.get('implied_volatility') or 0},
    "model_estimated_profit_probability": {judge.get('model_estimated_profit_probability', 0)},
    "position_size": "0R|0.25R|0.5R|1R",
    "max_loss": "premium_paid",
    "reason": "string in Chinese"
  }},
  "alternative_contract": {{
    "contract": "string or null",
    "action": "buy_to_open|none",
    "preferred_dte": "45-90",
    "preferred_moneyness": "10%-35% OTM",
    "reason": "string in Chinese"
  }},
  "take_profit_plan": ["list in Chinese"],
  "invalidation": ["list in Chinese"],
  "notes": ["list in Chinese"]
}}

Action rules:
- strong_follow ONLY if leakage >= 90, tradeability >= 80, no liquidity issue
- small_follow if leakage >= 75, tradeability >= 65
- observe_only if interesting but OI pending or poor liquidity
- avoid if bad spread, extreme IV, news priced in, or likely noise

Position sizing:
- 0R for avoid
- 0.25R for observe/small speculative
- 0.5R for good but unconfirmed
- 1R only with strong evidence + OI confirmation

Current scores: leakage={leakage}, tradeability={tradeability}. Apply rules accordingly."""

            result = await deepseek.chat(
                system_prompt=TRADE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                model=settings.deepseek_reasoning_model,
            )

            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({
                "trade_bias": result.get("trade_bias", "neutral"),
                "primary_action": result.get("primary_action", "observe_only"),
                "original_contract": result.get("original_contract", {}),
                "alternative_contract": result.get("alternative_contract", {}),
                "take_profit_plan": result.get("take_profit_plan", []),
                "invalidation": result.get("invalidation", []),
                "notes": result.get("notes", []),
                "score": leakage,
            })
            self.logger.info("trade_construction_complete", action=output["primary_action"])
            return output
        except Exception as e:
            self.logger.error("trade_construction_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e), "primary_action": "avoid"}
