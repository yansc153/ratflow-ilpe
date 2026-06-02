import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import yfinance as yf
from app.data_sources.unusual_options_provider import UnusualOptionsProvider
from app.config import settings
from app.logging_config import logger


class YFinanceScanner(UnusualOptionsProvider):
    provider_name = "yfinance"

    async def fetch_unusual_options(self) -> List[Dict[str, Any]]:
        tickers = [t.strip() for t in settings.watchlist_tickers.split(",") if t.strip()]
        all_alerts = []

        loop = asyncio.get_event_loop()

        for ticker in tickers[:200]:
            try:
                alerts = await loop.run_in_executor(None, self._scan_ticker, ticker)
                all_alerts.extend(alerts)
                await asyncio.sleep(0.3)  # Rate limit: don't hammer Yahoo
            except Exception as e:
                logger.warning("yfinance_ticker_failed", ticker=ticker, error=str(e))

        logger.info("yfinance_scan_done", tickers_scanned=len(tickers[:200]), alerts_found=len(all_alerts))
        return all_alerts

    def _scan_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        alerts = []
        try:
            t = yf.Ticker(ticker)
            expirations = t.options
            if not expirations:
                return alerts

            # Get real underlying stock price from fast_info or history
            try:
                info = t.fast_info
                underlying_price = float(info.get("lastPrice", 0) or info.get("regularMarketPreviousClose", 0) or 0)
            except Exception:
                try:
                    hist = t.history(period="1d")
                    underlying_price = float(hist["Close"].iloc[-1]) if not hist.empty else 0
                except Exception:
                    underlying_price = 0

            if underlying_price <= 0:
                return alerts

            today = datetime.now()
            for exp_date in expirations[:4]:
                try:
                    exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
                    dte = (exp_dt - today).days
                except ValueError:
                    continue

                if dte < 7 or dte > 90:
                    continue

                try:
                    chain = t.option_chain(exp_date)
                except Exception:
                    continue

                calls_df = chain.calls if hasattr(chain, 'calls') and chain.calls is not None else None
                puts_df = chain.puts if hasattr(chain, 'puts') and chain.puts is not None else None

                for df, opt_type in [(calls_df, "CALL"), (puts_df, "PUT")]:
                    if df is None or (hasattr(df, 'empty') and df.empty):
                        continue
                    for _, row in df.iterrows():
                        alert = self._check_row(ticker, row, exp_date, dte, opt_type, underlying_price)
                        if alert:
                            alerts.append(alert)
        except Exception as e:
            logger.debug("yfinance_ticker_error", ticker=ticker, error=str(e))

        return alerts

    def _check_row(self, ticker: str, row, expiry: str, dte: int, opt_type: str, underlying_price: float = 0) -> Optional[Dict[str, Any]]:
        volume = int(row.get("volume", 0) or 0)
        oi = int(row.get("openInterest", 0) or 0)
        last_price = float(row.get("lastPrice", 0) or 0)

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
            "option_type": opt_type,
            "strike": float(row.get("strike", 0)),
            "expiry": expiry,
            "dte": dte,
            "volume": volume,
            "open_interest": oi,
            "bid": float(row.get("bid", 0)) if row.get("bid") and float(row.get("bid", 0)) > 0 else None,
            "ask": float(row.get("ask", 0)) if row.get("ask") and float(row.get("ask", 0)) > 0 else None,
            "last_price": last_price,
            "implied_volatility": float(row.get("impliedVolatility", 0)) if row.get("impliedVolatility") and float(row.get("impliedVolatility", 0)) > 0 else None,
            "premium": premium,
            "underlying_price": underlying_price,
            "raw_json": row.to_dict(),
            "source": "yfinance",
        }
        return self._normalize_sync(raw)

    def _normalize_sync(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
            logger.warning("yfinance_normalize_failed", error=str(e))
            return None

    async def normalize_option_alert(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._normalize_sync(raw)
