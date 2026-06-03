from typing import Dict, Any, List
from bs4 import BeautifulSoup
import httpx
from app.data_sources.base import DataSourceBase
from app.config import settings
from app.logging_config import logger


class NewsSearchAdapter(DataSourceBase):
    source_name = "news_search"
    duckduckgo_html_url = "https://html.duckduckgo.com/html/"

    async def fetch(self, query: str = "", **kwargs) -> Dict[str, Any]:
        logger.info("news_search_fetch", query=query)
        results = await self.search_news(query=query, max_results=kwargs.get("max_results", 8))
        if not results:
            return self.unavailable_response("No search results found")
        return {
            "source": self.source_name,
            "status": "ok",
            "data": results,
        }

    async def search_news(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        if not query:
            return []
        if settings.search_provider != "duckduckgo":
            logger.info("news_search_provider_unavailable", provider=settings.search_provider)
            return []

        headers = {
            "User-Agent": "Mozilla/5.0",
        }
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers, follow_redirects=True) as client:
            try:
                response = await client.get(self.duckduckgo_html_url, params={"q": query})
                response.raise_for_status()
            except Exception as e:
                logger.warning("news_search_failed", query=query, error=str(e))
                return []

        return self._parse_duckduckgo_results(response.text, max_results=max_results)

    @staticmethod
    def _parse_duckduckgo_results(html: str, max_results: int = 10) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for node in soup.select(".result"):
            if len(results) >= max_results:
                break
            link = node.select_one(".result__a")
            snippet = node.select_one(".result__snippet")
            if not link:
                continue
            title = link.get_text(" ", strip=True)
            url = link.get("href", "")
            snippet_text = snippet.get_text(" ", strip=True) if snippet else ""
            if not title or not url:
                continue
            results.append({
                "title": title,
                "url": url,
                "snippet": snippet_text,
                "source_name": NewsSearchAdapter._infer_source_name(url),
            })
        return results

    @staticmethod
    def _infer_source_name(url: str) -> str:
        try:
            host = url.split("//", 1)[-1].split("/", 1)[0]
            return host.replace("www.", "")
        except Exception:
            return "unknown"
