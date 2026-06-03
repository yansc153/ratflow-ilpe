from typing import Dict, Any, List

from app.data_sources.base import DataSourceBase
from app.logging_config import logger


class YFinanceResearchAdapter(DataSourceBase):
    source_name = "yfinance_research"

    async def fetch(self, ticker: str = "", **kwargs) -> Dict[str, Any]:
        if not ticker:
            return self.unavailable_response("No ticker provided")
        try:
            import yfinance as yf
        except Exception as e:
            return self.error_response(str(e))

        try:
            stock = yf.Ticker(ticker)
            calendar = stock.calendar or {}
            earnings_dates = self._format_earnings_dates(stock)
            news = self._format_news(stock.news or [], limit=kwargs.get("news_limit", 5))
            fast_info = dict(stock.fast_info) if stock.fast_info else {}
            return {
                "source": self.source_name,
                "status": "ok",
                "data": {
                    "calendar": self._sanitize_calendar(calendar),
                    "earnings_dates": earnings_dates,
                    "news": news,
                    "fast_info": self._subset_fast_info(fast_info),
                },
            }
        except Exception as e:
            logger.warning("yfinance_research_failed", ticker=ticker, error=str(e))
            return self.error_response(str(e))

    @staticmethod
    def _sanitize_calendar(calendar: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {}
        for key, value in calendar.items():
            if isinstance(value, list):
                sanitized[key] = [str(v) for v in value[:3]]
            else:
                sanitized[key] = str(value)
        return sanitized

    @staticmethod
    def _format_earnings_dates(stock) -> List[Dict[str, Any]]:
        try:
            df = stock.earnings_dates
        except Exception:
            return []
        if df is None or getattr(df, "empty", True):
            return []
        rows = []
        for idx, row in df.head(4).iterrows():
            rows.append({
                "earnings_date": str(idx),
                "eps_estimate": None if row.get("EPS Estimate") is None else float(row.get("EPS Estimate")),
                "reported_eps": None if row.get("Reported EPS") is None else float(row.get("Reported EPS")),
                "surprise_pct": None if row.get("Surprise(%)") is None else float(row.get("Surprise(%)")),
            })
        return rows

    @staticmethod
    def _format_news(items: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        out = []
        for item in items[:limit]:
            content = item.get("content", {})
            out.append({
                "title": content.get("title", ""),
                "summary": content.get("summary", ""),
                "url": content.get("canonicalUrl", {}).get("url", ""),
                "provider": content.get("provider", {}).get("displayName", ""),
                "published_at": content.get("pubDate", ""),
            })
        return out

    @staticmethod
    def _subset_fast_info(fast_info: Dict[str, Any]) -> Dict[str, Any]:
        keep = [
            "lastPrice",
            "marketCap",
            "shares",
            "tenDayAverageVolume",
            "threeMonthAverageVolume",
            "yearHigh",
            "yearLow",
        ]
        return {k: fast_info.get(k) for k in keep if k in fast_info}
