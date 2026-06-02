from typing import List, Dict, Any, Optional
from app.data_sources.unusual_options_provider import UnusualOptionsProvider
from app.logging_config import logger


class BarchartPublicAdapter(UnusualOptionsProvider):
    provider_name = "barchart_public"

    async def fetch_unusual_options(self) -> List[Dict[str, Any]]:
        logger.info("barchart_fetch_attempt")
        return []  # Graceful: returns empty, not error

    async def normalize_option_alert(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return {
                "source": self.provider_name,
                "ticker": raw.get("ticker", "").upper(),
                "option_type": raw.get("option_type", "CALL").upper(),
                "strike": float(raw.get("strike", 0)),
                "expiry": raw.get("expiry", ""),
                "dte": int(raw.get("dte", 0)) if raw.get("dte") else None,
                "volume": int(raw.get("volume", 0)),
                "open_interest": int(raw.get("open_interest", 0)),
                "bid": float(raw.get("bid", 0)) if raw.get("bid") else None,
                "ask": float(raw.get("ask", 0)) if raw.get("ask") else None,
                "last_price": float(raw.get("last_price", 0)) if raw.get("last_price") else None,
                "implied_volatility": float(raw.get("implied_volatility", 0)) if raw.get("implied_volatility") else None,
                "premium": float(raw.get("premium", 0)) if raw.get("premium") else None,
                "underlying_price": float(raw.get("underlying_price", 0)) if raw.get("underlying_price") else None,
                "raw_json": raw,
            }
        except Exception as e:
            logger.error("barchart_normalize_failed", error=str(e))
            return None
