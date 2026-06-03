from typing import Dict, Any, List

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.data_sources.base import DataSourceBase
from app.data_sources.news_search import NewsSearchAdapter
from app.logging_config import logger


class WebsiteResearchAdapter(DataSourceBase):
    source_name = "website_research"

    async def fetch(self, url: str = "", **kwargs) -> Dict[str, Any]:
        if not url:
            return self.unavailable_response("No URL provided")

        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, headers=headers, follow_redirects=True) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except Exception as e:
                logger.warning("website_research_failed", url=url, error=str(e))
                return self.error_response(str(e))

        return {
            "source": self.source_name,
            "status": "ok",
            "data": self._extract_page_summary(response.text, str(response.url)),
        }

    @staticmethod
    def _extract_page_summary(html: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        description = meta.get("content", "").strip() if meta else ""
        paragraphs: List[str] = []
        for tag in soup.select("p"):
            text = tag.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)
            if len(" ".join(paragraphs)) > 800:
                break
        return {
            "url": url,
            "title": title,
            "description": description,
            "text_excerpt": " ".join(paragraphs)[:1200],
        }


class JobsResearchAdapter(DataSourceBase):
    source_name = "jobs_research"

    async def fetch(self, company: str = "", **kwargs) -> Dict[str, Any]:
        if not company:
            return self.unavailable_response("No company provided")
        search = NewsSearchAdapter()
        query = f'{company} careers jobs AI ML LLM data science'
        results = await search.search_news(query, max_results=6)
        return {"source": self.source_name, "status": "ok", "data": results}


class SocialResearchAdapter(DataSourceBase):
    source_name = "social_research"

    async def fetch(self, ticker: str = "", **kwargs) -> Dict[str, Any]:
        if not ticker:
            return self.unavailable_response("No ticker provided")
        search = NewsSearchAdapter()
        query = f'{ticker} reddit stocktwits x discussion options unusual'
        results = await search.search_news(query, max_results=6)
        return {"source": self.source_name, "status": "ok", "data": results}


class PatentsResearchAdapter(DataSourceBase):
    source_name = "patents_research"

    async def fetch(self, company: str = "", **kwargs) -> Dict[str, Any]:
        if not company:
            return self.unavailable_response("No company provided")
        search = NewsSearchAdapter()
        query = f'{company} patent litigation IP licensing'
        results = await search.search_news(query, max_results=6)
        return {"source": self.source_name, "status": "ok", "data": results}


class GovContractsResearchAdapter(DataSourceBase):
    source_name = "gov_contracts_research"

    async def fetch(self, company: str = "", **kwargs) -> Dict[str, Any]:
        if not company:
            return self.unavailable_response("No company provided")
        search = NewsSearchAdapter()
        query = f'{company} site:sam.gov OR site:defense.gov contract award procurement'
        results = await search.search_news(query, max_results=6)
        return {"source": self.source_name, "status": "ok", "data": results}


class PriceDataAdapter(DataSourceBase):
    source_name = "price_data"

    async def fetch(self, ticker: str = "", **kwargs) -> Dict[str, Any]:
        if not ticker:
            return self.unavailable_response("No ticker provided")
        try:
            import yfinance as yf
        except Exception as e:
            return self.error_response(str(e))

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=kwargs.get("period", "1mo"))
            if hist.empty:
                return self.unavailable_response("No price history")
            latest = float(hist["Close"].iloc[-1])
            five_day_return = None
            if len(hist) >= 6:
                five_day_return = round((latest / float(hist["Close"].iloc[-6]) - 1) * 100, 2)
            month_return = round((latest / float(hist["Close"].iloc[0]) - 1) * 100, 2)
            return {
                "source": self.source_name,
                "status": "ok",
                "data": {
                    "latest_close": latest,
                    "five_day_return_pct": five_day_return,
                    "month_return_pct": month_return,
                    "rows": len(hist),
                },
            }
        except Exception as e:
            logger.warning("price_data_failed", ticker=ticker, error=str(e))
            return self.error_response(str(e))
