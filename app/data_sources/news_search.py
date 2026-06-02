from typing import Dict, Any, List
from app.data_sources.base import DataSourceBase
from app.config import settings
from app.logging_config import logger


class NewsSearchAdapter(DataSourceBase):
    source_name = "news_search"

    async def fetch(self, query: str = "", **kwargs) -> Dict[str, Any]:
        logger.info("news_search_fetch", query=query)
        if settings.search_provider == "duckduckgo":
            return self.unavailable_response("News search not configured for MVP — use LLM-based research agents")
        return self.unavailable_response(f"Search provider {settings.search_provider} not configured")

    async def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        return []  # Graceful: LLM agents handle research through their own knowledge
