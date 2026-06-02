from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from typing import Dict, Any, Optional
from app.logging_config import logger

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class ReportRenderer:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape(enabled_extensions=[]),
        )

    def render_initial_report(self, ctx: Dict[str, Any]) -> str:
        try:
            template = self.env.get_template("discord_initial_report.md.j2")
            return template.render(**ctx)
        except Exception as e:
            logger.error("render_initial_report_failed", error=str(e))
            return self._fallback_initial(ctx)

    def render_oi_update(self, ctx: Dict[str, Any]) -> str:
        try:
            template = self.env.get_template("discord_oi_update.md.j2")
            return template.render(**ctx)
        except Exception as e:
            logger.error("render_oi_update_failed", error=str(e))
            return self._fallback_oi_update(ctx)

    def render_outcome_update(self, ctx: Dict[str, Any]) -> str:
        try:
            template = self.env.get_template("discord_outcome_update.md.j2")
            return template.render(**ctx)
        except Exception as e:
            logger.error("render_outcome_update_failed", error=str(e))
            return self._fallback_outcome(ctx)

    def _fallback_initial(self, ctx: Dict[str, Any]) -> str:
        return f"""🐀 **RATFLOW 老鼠仓嫌疑报告**

**Case:** {ctx.get('case_uid', 'N/A')}
**Ticker:** {ctx.get('ticker', 'N/A')}
**方向:** {ctx.get('direction_label', 'N/A')}

**总评分:**
Leakage Score: {ctx.get('leakage_score', 'N/A')}/100
Tradeability Score: {ctx.get('tradeability_score', 'N/A')}/100

**交易建议:** {ctx.get('primary_action', 'N/A')}
**原单:** {ctx.get('original_contract_label', 'N/A')}

这是基于公开数据的概率化研究报告，不是投资建议。"""

    def _fallback_oi_update(self, ctx: Dict[str, Any]) -> str:
        return f"""🐀 **RATFLOW OI确认更新**

**Case:** {ctx.get('case_uid', 'N/A')}
**OI Change:** {ctx.get('oi_change', 'N/A')}
**OI Confirmation Ratio:** {ctx.get('oi_confirmation_ratio', 'N/A')}%
**Status:** {ctx.get('oi_status', 'N/A')}"""

    def _fallback_outcome(self, ctx: Dict[str, Any]) -> str:
        return f"""🐀 **RATFLOW 结果追踪**

**Case:** {ctx.get('case_uid', 'N/A')}
**Horizon:** {ctx.get('horizon', 'N/A')}
**Underlying Return:** {ctx.get('underlying_return', 'N/A')}%"""


report_renderer = ReportRenderer()
