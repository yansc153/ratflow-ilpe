import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from app.data_sources.unusual_options_provider import UnusualOptionsProvider
from app.config import settings
from app.logging_config import logger


class TradierAdapter(UnusualOptionsProvider):
    provider_name = "tradier"

    BASE_URL = "https://sandbox.tradier.com/v1"

    def __init__(self):
        self.token = settings.tradier_sandbox_token
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        self._rate_limit = asyncio.Semaphore(60)  # 60 concurrent max (120 req/min but be safe)
        self._last_request = 0.0

    async def _rate_limited_get(self, url: str, params: dict = None) -> dict:
        async with self._rate_limit:
            await asyncio.sleep(0.5)  # 120 req/min = 2/sec, stay safe at 0.5s
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=self._headers, params=params or {})
                resp.raise_for_status()
                return resp.json()

    async def fetch_unusual_options(self) -> List[Dict[str, Any]]:
        if not self.token:
            logger.info("tradier_no_token", msg="Tradier sandbox token not set, skipping")
            return []

        tickers = [t.strip() for t in settings.watchlist_tickers.split(",") if t.strip()]
        all_alerts = []

        for ticker in tickers[:150]:  # Cap at 150 to stay within rate limits
            try:
                alerts = await self._scan_ticker(ticker)
                all_alerts.extend(alerts)
            except Exception as e:
                logger.warning("tradier_ticker_failed", ticker=ticker, error=str(e))

        logger.info("tradier_scan_done", tickers_scanned=len(tickers[:150]), alerts_found=len(all_alerts))
        return all_alerts

    async def _scan_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            exp_data = await self._rate_limited_get(
                f"{self.BASE_URL}/markets/options/expirations",
                params={"symbol": ticker},
            )
        except Exception:
            return []

        dates = (exp_data.get("expirations") or {}).get("date", [])
        if not dates:
            return []

        today = datetime.now()
        alerts = []

        for exp_date in dates[:4]:  # Check only next 4 expirations
            try:
                dte = (datetime.strptime(exp_date, "%Y-%m-%d") - today).days
            except ValueError:
                continue

            if dte < 1 or dte > 90:
                continue

            try:
                chain_data = await self._rate_limited_get(
                    f"{self.BASE_URL}/markets/options/chains",
                    params={"symbol": ticker, "expiration": exp_date, "greeks": "false"},
                )
            except Exception:
                continue

            options = (chain_data.get("options") or {}).get("option", [])
            if not options:
                continue

            for opt in options:
                alert = self._check_contract(ticker, opt, exp_date, dte)
                if alert:
                    alerts.append(alert)

        return alerts

    def _check_contract(self, ticker: str, opt: dict, expiry: str, dte: int) -> Optional[Dict[str, Any]]:
        volume = opt.get("volume", 0) or 0
        oi = opt.get("open_interest", 0) or 0
        last_price = opt.get("last", 0) or 0

        if volume == 0 or last_price == 0 or oi == 0:
            return None

        vol_oi = volume / max(oi, 1)
        if vol_oi < 3.0:
            return None

        premium = volume * last_price * 100
        if premium < 25_000:
            return None

        raw = {
            "ticker": ticker,
            "option_type": opt.get("option_type", "call").upper(),
            "strike": opt.get("strike", 0),
            "expiry": expiry,
            "dte": dte,
            "volume": volume,
            "open_interest": oi,
            "bid": opt.get("bid"),
            "ask": opt.get("ask"),
            "last_price": last_price,
            "implied_volatility": opt.get("implied_volatility"),
            "underlying_price": opt.get("underlying_price") or opt.get("last"),
            "raw_json": opt,
            "source": "tradier",
        }
        return self.normalize_option_alert(raw)

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
            logger.warning("tradier_normalize_failed", error=str(e))
            return None
