from typing import Dict, Any, Optional
from app.data_sources.base import DataSourceBase
from app.logging_config import logger


class YahooOptionsAdapter(DataSourceBase):
    source_name = "yahoo_options"

    async def fetch(self, ticker: str = "", **kwargs) -> Dict[str, Any]:
        logger.info("yahoo_options_fetch", ticker=ticker)
        return self.unavailable_response("Yahoo options scraping not configured for MVP")

    async def get_option_chain(self, ticker: str, expiry: Optional[str] = None) -> Dict[str, Any]:
        return self.unavailable_response("Option chain data not available")

    async def get_current_oi(self, ticker: str, strike: float, expiry: str, option_type: str) -> Optional[int]:
        logger.info("yahoo_oi_check", ticker=ticker, strike=strike, expiry=expiry)
        return None  # Graceful: returns None for MVP
