from typing import Dict, Any, List
from app.logging_config import logger


class EvidenceMerger:
    @staticmethod
    def merge(agent_outputs: Dict[str, Any], noise_output: Dict[str, Any] = None) -> Dict[str, Any]:
        all_positive = []
        all_negative = []
        all_uncertainties = []
        all_errors = []
        agent_summaries = []

        for name, output in agent_outputs.items():
            if not isinstance(output, dict):
                continue
            if "error" in output:
                all_errors.append({"agent": name, "error": output["error"]})
                continue

            all_positive.extend(output.get("positive_evidence", []))
            all_negative.extend(output.get("negative_evidence", []))
            all_uncertainties.extend(output.get("uncertainties", []))
            if output.get("summary"):
                agent_summaries.append({"agent": name, "summary": output["summary"]})

        if noise_output and isinstance(noise_output, dict):
            all_negative.extend(noise_output.get("red_flags", []))
            all_uncertainties.append(f"Noise assessment: {noise_output.get('summary', 'N/A')}")

        score = EvidenceMerger._compute_evidence_score(all_positive, all_negative)

        merged = {
            "positive_evidence_count": len(all_positive),
            "negative_evidence_count": len(all_negative),
            "all_positive_evidence": all_positive,
            "all_negative_evidence": all_negative,
            "uncertainties": all_uncertainties,
            "errors": all_errors,
            "agent_summaries": agent_summaries,
            "evidence_score": score,
            "agent_outputs": agent_outputs,
        }
        logger.info("evidence_merged", positive=len(all_positive), negative=len(all_negative), score=score)
        return merged

    @staticmethod
    def _compute_evidence_score(positive: list, negative: list) -> int:
        quality_map = {"A": 4, "B": 3, "C": 2, "D": 1}
        pos_score = sum(quality_map.get(e.get("quality", "C").upper(), 2) for e in positive if isinstance(e, dict))
        neg_count = len([e for e in negative if e])
        total = pos_score - neg_count * 2
        return max(0, min(100, total * 5 + 30))
