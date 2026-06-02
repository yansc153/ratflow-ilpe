from typing import Dict, Any, List
from app.data_sources.base import DataSourceBase
from app.logging_config import logger


class SECEdgarAdapter(DataSourceBase):
    source_name = "sec_edgar"

    async def fetch(self, ticker: str = "", **kwargs) -> Dict[str, Any]:
        logger.info("sec_edgar_fetch", ticker=ticker)
        return self.unavailable_response("SEC EDGAR adapter not implemented for MVP")

    async def get_recent_filings(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        logger.info("sec_edgar_filings", ticker=ticker)
        return []  # Graceful empty
