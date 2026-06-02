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

            user_prompt = f"""Research whether {company} ({ticker}) may have a regulatory, legal, patent, or FDA catalyst.

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
            return output
        except Exception as e:
            self.logger.error("regulatory_legal_patent_failed", error=str(e))
            return {"agent_name": self.agent_name, "error": str(e)}
