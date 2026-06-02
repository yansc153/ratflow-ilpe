from app.logging_config import logger


class SourceCitationService:
    @staticmethod
    def format_evidence(evidence_items: list[dict], polarity: str = "positive") -> list[dict]:
        formatted = []
        for item in evidence_items:
            if not isinstance(item, dict):
                continue
            formatted.append({
                "quality": item.get("quality", "C"),
                "title": item.get("title", "Unknown"),
                "source_name": item.get("source_name", "Unknown"),
                "url": item.get("url", ""),
                "date": item.get("date", ""),
                "snippet": item.get("snippet", ""),
                "relevance": item.get("relevance", 0.5),
                "type": item.get("type", "general"),
            })
        return formatted

    @staticmethod
    def build_source_map(evidence_items: list[dict]) -> dict:
        sources = {}
        for item in evidence_items:
            url = item.get("url", "")
            if url and url not in sources:
                sources[url] = {
                    "source_name": item.get("source_name", "Unknown"),
                    "url": url,
                    "date": item.get("date", ""),
                }
        return sources


citation_service = SourceCitationService()
