from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from app.logging_config import logger


AGENT_SYSTEM_PROMPT = """You are a public-data financial research subagent.

You may use only public information.
You must not infer or claim actual insider trading.
You must return valid JSON only.
Every evidence item must include source, URL if available, date if available, snippet, and relevance.
If evidence is unavailable, say unavailable.
Do not hallucinate sources.
Separate positive evidence from negative evidence.
Use conservative confidence."""


class BaseAgent(ABC):
    agent_name: str = "base"

    def __init__(self):
        self.logger = logger.bind(agent=self.agent_name)

    @abstractmethod
    async def run(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def base_output(self, case_id: str) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "case_id": case_id,
            "score": 0,
            "confidence": "low",
            "summary": "",
            "positive_evidence": [],
            "negative_evidence": [],
            "uncertainties": [],
            "errors": [],
        }

    def format_evidence(self, items: list[dict], polarity: str) -> list[dict]:
        formatted = []
        for item in items:
            formatted.append({
                "type": item.get("type", "general"),
                "quality": item.get("quality", "C"),
                "title": item.get("title", ""),
                "source_name": item.get("source_name", ""),
                "url": item.get("url", ""),
                "date": item.get("date", ""),
                "snippet": item.get("snippet", ""),
                "relevance": item.get("relevance", 0.5),
            })
        return formatted

    def get_validated_bucket(self, case_data: Dict[str, Any], topic: str) -> list[dict]:
        validated = case_data.get("validated_evidence", {})
        return ((validated.get("by_hypothesis") or {}).get(topic, {}) or {}).get("evidence", []) or []

    def get_source_context(self, case_data: Dict[str, Any], key: str) -> Dict[str, Any]:
        return (case_data.get("source_context") or {}).get(key, {}) or {}

    @staticmethod
    def render_validated_items(items: list[dict], limit: int = 6) -> str:
        if not items:
            return "No validated evidence available."
        lines = []
        for item in items[:limit]:
            lines.append(
                f"- [{item.get('reliability', 'D')}] {item.get('title', '')} | "
                f"{item.get('source_name', '')} | {item.get('snippet', '')[:180]}"
            )
        return "\n".join(lines)
