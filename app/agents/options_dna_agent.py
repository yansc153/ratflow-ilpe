from typing import Dict, Any
from app.agents.base import BaseAgent
from app.config import settings
from app.logging_config import logger


class OptionsDNAAgent(BaseAgent):
    agent_name = "options_dna_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            contract = case_data.get("normalized_contract", {})
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update(self._score(alert, contract))
            logger.info(
                "options_dna_complete",
                score=output["options_dna_score"],
                route=output.get("dna_route"),
                anomaly_score=output.get("anomaly_score"),
                contract_quality_score=output.get("contract_quality_score"),
                convexity_score=output.get("convexity_score"),
            )
            return output
        except Exception as e:
            logger.error("options_dna_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e), "options_dna_score": 0}

    def _score(self, alert: dict, contract: dict) -> dict:
        score = 0
        findings = []
        red_flags = []

        volume = contract.get("volume", 0) or 0
        oi = contract.get("open_interest", 0) or 0
        ratio = contract.get("volume_oi_ratio") or 0
        premium = contract.get("premium", 0) or 0
        last_price = contract.get("last_price", 0) or 0
        if premium <= 0 and volume and last_price:
            premium = volume * last_price * 100
        elif premium <= 0 and volume and contract.get("mid_price"):
            premium = volume * (contract.get("mid_price") or 0) * 100

        anomaly_score = 0
        contract_quality_score = 0
        convexity_score = 0

        if ratio < 1.0:
            findings.append("Volume/OI < 1.0: 无异常")
        elif 1.0 <= ratio < 2.0:
            score += 8
            anomaly_score += 8
            findings.append(f"Volume/OI = {ratio:.1f}: 轻微异常 (+8)")
        elif 2.0 <= ratio < 5.0:
            score += 15
            anomaly_score += 15
            findings.append(f"Volume/OI = {ratio:.1f}: 明显异常 (+15)")
        else:
            score += 22
            anomaly_score += 22
            convexity_score += 10
            findings.append(f"Volume/OI = {ratio:.1f}: 严重异常 (+22)")

        dte = contract.get("dte") or 0
        if 14 <= dte <= 120:
            score += 15
            contract_quality_score += 15
            findings.append(f"DTE={dte}: 理想时间窗口 (+15)")
        elif 7 <= dte <= 13:
            score += 5
            contract_quality_score += 5
            anomaly_score += 4
            convexity_score += 18
            findings.append(f"DTE={dte}: 较短时间窗口 (+5)")
        elif 1 <= dte <= 6:
            score += 2
            contract_quality_score += 2
            anomaly_score += 8
            convexity_score += 28
            findings.append(f"DTE={dte}: 超短线高凸性窗口 (+2)")
        elif 121 <= dte <= 180:
            score += 5
            contract_quality_score += 5
            findings.append(f"DTE={dte}: 较长时间窗口 (+5)")
        elif dte > 180:
            score += 3
            contract_quality_score += 3
            findings.append(f"DTE={dte}: 超长时间窗口 (+3)")
        else:
            score -= 10
            contract_quality_score -= 10
            red_flags.append(f"DTE={dte}: 临近到期 (-10)")

        otm_pct = contract.get("otm_pct")
        if otm_pct is not None:
            if 5 <= abs(otm_pct) <= 60:
                score += 15
                anomaly_score += 8
                convexity_score += 7
                findings.append(f"OTM={otm_pct:.1f}%: 理想虚值范围 (+15)")
            elif 0 <= abs(otm_pct) < 5:
                score += 8
                anomaly_score += 4
                findings.append(f"OTM={otm_pct:.1f}%: 接近平值 (+8)")
            elif 60 < abs(otm_pct) <= 100:
                score += 5
                anomaly_score += 2
                convexity_score += 15
                findings.append(f"OTM={otm_pct:.1f}%: 深度虚值 (+5)")
            elif 100 < abs(otm_pct) <= 150 and dte <= 13:
                score += 2
                anomaly_score += 10
                convexity_score += 18
                findings.append(f"OTM={otm_pct:.1f}%: 超深度虚值但具备高凸性 (+2)")
            else:
                score -= 8
                contract_quality_score -= 8
                red_flags.append(f"OTM={otm_pct:.1f}%: 极度虚值 (-8)")

        iv_change = contract.get("iv_change")
        if iv_change is not None:
            if 0.05 <= abs(iv_change) <= 0.40:
                score += 10
                anomaly_score += 6
                contract_quality_score += 4
                findings.append(f"IV change={iv_change:.0%}: 适度波动 (+10)")
            elif abs(iv_change) > 0.80:
                score -= 8
                contract_quality_score -= 8
                red_flags.append(f"IV change={iv_change:.0%}: 极端波动 (-8)")
            else:
                if dte <= 13 and ratio >= 3:
                    convexity_score += 8
                findings.append(f"IV change={iv_change:.0%}: 轻微波动")

        stock_move = contract.get("underlying_move_5d")
        if stock_move is not None:
            if abs(stock_move) < 0.05:
                score += 10
                anomaly_score += 6
                convexity_score += 6
                findings.append(f"Stock 5D move={stock_move:.1%}: 价格滞后 (+10)")
            elif abs(stock_move) < 0.10:
                anomaly_score += 3
            elif abs(stock_move) > 0.20:
                score -= 12
                contract_quality_score -= 4
                anomaly_score -= 4
                red_flags.append(f"Stock 5D move={stock_move:.1%}: 已大幅波动 (-12)")

        bid = contract.get("bid") or 0
        ask = contract.get("ask") or 0
        mid = contract.get("mid_price") or 0
        if mid > 0 and bid > 0 and ask > 0:
            spread_pct = (ask - bid) / mid
            if spread_pct > 0.60:
                score -= 20
                contract_quality_score -= 20
                red_flags.append(f"Bid/Ask spread={spread_pct:.0%}: 极差 (-20)")
            elif spread_pct > 0.35:
                score -= 10
                contract_quality_score -= 10
                red_flags.append(f"Bid/Ask spread={spread_pct:.0%}: 较差 (-10)")
            elif spread_pct <= 0.20:
                score += 5
                contract_quality_score += 5
                findings.append(f"Bid/Ask spread={spread_pct:.0%}: 流动性较好 (+5)")

        if premium >= 1_000_000:
            score += 10
            anomaly_score += 10
            convexity_score += 10
            findings.append(f"Premium=${premium:,.0f}: 大额权利金 (+10)")
        elif premium >= 250_000:
            score += 6
            anomaly_score += 10
            convexity_score += 8
            findings.append(f"Premium=${premium:,.0f}: 较大权利金 (+6)")
        elif premium >= 75_000:
            score += 3
            anomaly_score += 3
            convexity_score += 4
            findings.append(f"Premium=${premium:,.0f}: 有意义权利金 (+3)")

        score = max(0, min(100, score))
        anomaly_score = max(0, min(100, anomaly_score))
        contract_quality_score = max(0, min(100, contract_quality_score + 40))
        convexity_score = max(0, min(100, convexity_score))

        direction = contract.get("direction", "unclear")
        contract_quality = "poor"
        if score >= 70:
            contract_quality = "excellent"
        elif score >= 55:
            contract_quality = "good"
        elif score >= 40:
            contract_quality = "mixed"

        research_priority = "none"
        if score >= 65:
            research_priority = "urgent"
        elif score >= 50:
            research_priority = "full"
        elif score >= 35:
            research_priority = "light"

        dna_route = "LOW_PRIORITY"
        block_reason = ""
        if premium < 25_000 or ratio < 2.0 or (mid <= 0 and last_price <= 0):
            dna_route = "DROP_NOISE"
            block_reason = "insufficient anomaly or untradeable contract"
        elif anomaly_score >= 55 or score >= settings.min_options_dna_research_score or score >= max(40, settings.min_options_dna_research_score - 5):
            dna_route = "FULL_RESEARCH"
        elif 1 <= dte <= 13 and anomaly_score >= 45 and convexity_score >= 45 and premium >= 75_000 and ratio >= 3.0:
            dna_route = "SPECULATIVE_RESEARCH"
            findings.append("短线高凸性样本：进入 speculative research")
        elif score < 35:
            dna_route = "DROP_NOISE"
            block_reason = "composite dna score too weak"

        return {
            "options_dna_score": score,
            "anomaly_score": anomaly_score,
            "contract_quality_score": contract_quality_score,
            "convexity_score": convexity_score,
            "dna_route": dna_route,
            "block_reason": block_reason,
            "direction": direction,
            "contract_quality": contract_quality,
            "research_priority": research_priority,
            "key_findings": findings,
            "red_flags": red_flags,
        }
