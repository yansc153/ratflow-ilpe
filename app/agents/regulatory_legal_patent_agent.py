from typing import Dict, Any
from app.agents.base import BaseAgent, AGENT_SYSTEM_PROMPT
from app.services.deepseek_client import deepseek


class RegulatoryLegalPatentAgent(BaseAgent):
    agent_name = "regulatory_legal_patent_agent"

    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert = case_data.get("alert", {})
            ticker = alert.get("ticker", "")
            company = alert.get("company_name", ticker)
            validated_reg = self.get_validated_bucket(case_data, "regulatory")
            patents_ctx = self.get_source_context(case_data, "patents")
            search_ctx = self.get_source_context(case_data, "regulatory_search")

            user_prompt = f"""Research whether {company} ({ticker}) may have a regulatory, legal, patent, or FDA catalyst.

Validated regulatory evidence:
{self.render_validated_items(validated_reg)}

Retrieved patents/legal search context:
{patents_ctx.get('data', []) if patents_ctx else []}

Retrieved broader regulatory search context:
{search_ctx.get('data', []) if search_ctx else []}

Check public clues:
- FDA calendar dates (PDUFA, advisory committee) if pharmaceutical/biotech
- Clinical trial phases and readout dates (clinicaltrials.gov)
- Patent applications, grants, or litigation
- Major lawsuits (class action, IP, contract disputes)
- Regulatory approvals or rejections (FCC, EPA, FTC, etc.)
- Settlement agreements or judgments
- New regulations affecting the company's industry
- Import/export restrictions or trade policy changes
- Licensing agreements or IP transactions
- ANDA (generic drug) filings if applicable

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

Do not fabricate evidence. State limitations clearly."""

            result = await deepseek.chat(system_prompt=AGENT_SYSTEM_PROMPT, user_prompt=user_prompt)
            output = self.base_output(case_data.get("case_uid", "unknown"))
            output.update({k: v for k, v in result.items() if k in output})
            output["retrieved_context"] = {
                "validated_bucket": validated_reg,
                "patents": patents_ctx.get("data", []) if patents_ctx else [],
                "search": search_ctx.get("data", []) if search_ctx else [],
            }
            return output
        except Exception as e:
            self.logger.error("regulatory_legal_patent_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
