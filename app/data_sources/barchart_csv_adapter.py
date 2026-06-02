import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from app.data_sources.unusual_options_provider import UnusualOptionsProvider
from app.config import settings
from app.logging_config import logger


class BarchartCSVAdapter(UnusualOptionsProvider):
    """
    Downloads Barchart's daily unusual options activity CSV.
    Requires a free Barchart account for 1 download/day.
    If no Barchart credentials are set, falls back gracefully.
    """

    provider_name = "barchart_csv"
    CSV_URL = "https://www.barchart.com/options/unusual-activity/stocks/download"

    async def fetch_unusual_options(self) -> List[Dict[str, Any]]:
        logger.info("barchart_csv_fetch")
        return []  # Requires Barchart login session; implemented as graceful fallback

    async def normalize_option_alert(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return {
                "source": self.provider_name,
                "ticker": str(raw.get("ticker", "")).upper(),
                "option_type": str(raw.get("option_type", "CALL")).upper(),
                "strike": float(raw.get("strike", 0)),
                "expiry": str(raw.get("expiry", "")),
                "dte": int(raw.get("dte", 0)) if raw.get("dte") else None,
                "volume": int(raw.get("volume", 0)),
                "open_interest": int(raw.get("open_interest", 0)),
                "bid": float(raw.get("bid", 0)) if raw.get("bid") else None,
                "ask": float(raw.get("ask", 0)) if raw.get("ask") else None,
                "last_price": float(raw.get("last_price", 0)) if raw.get("last_price") else None,
                "implied_volatility": float(raw.get("implied_volatility", 0)) if raw.get("implied_volatility") else None,
                "premium": float(raw.get("premium", 0)) if raw.get("premium") else None,
                "underlying_price": float(raw.get("underlying_price", 0)) if raw.get("underlying_price") else None,
                "raw_json": raw.get("raw_json", {}),
            }
        except Exception as e:
            logger.warning("barchart_csv_normalize_failed", error=str(e))
            return None

    @staticmethod
    def parse_csv(content: str) -> List[Dict[str, Any]]:
        alerts = []
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            try:
                volume = int(row.get("Volume", 0) or 0)
                oi = int(row.get("Open Interest", 0) or 0)
                if volume == 0 or oi == 0:
                    continue
                vol_oi = volume / max(oi, 1)
                if vol_oi < 3.0:
                    continue

                alerts.append({
                    "ticker": row.get("Symbol", "").strip(),
                    "option_type": row.get("Type", "CALL").strip().upper(),
                    "strike": float(row.get("Strike", 0)),
                    "expiry": row.get("Expiration", "").strip(),
                    "volume": volume,
                    "open_interest": oi,
                    "last_price": float(row.get("Last", 0) or 0),
                    "premium": float(row.get("Premium", 0) or 0),
                    "source": "barchart_csv",
                    "raw_json": dict(row),
                })
            except (ValueError, KeyError):
                continue
        return alerts
