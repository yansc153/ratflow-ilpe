import asyncio
import json
import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import yfinance as yf
from app.data_sources.unusual_options_provider import UnusualOptionsProvider
from app.config import settings
from app.logging_config import logger


warnings.filterwarnings(
    "ignore",
    message="Timestamp.utcnow is deprecated.*",
    category=Warning,
    module="yfinance.*",
)


class YFinanceScanner(UnusualOptionsProvider):
    provider_name = "yfinance"

    async def fetch_unusual_options(self) -> List[Dict[str, Any]]:
        tickers = self._load_ticker_universe()
        batch = self._next_ticker_batch(tickers, settings.scan_batch_size)
        all_alerts = []

        loop = asyncio.get_event_loop()

        for ticker in batch:
            try:
                alerts = await loop.run_in_executor(None, self._scan_ticker, ticker)
                all_alerts.extend(alerts)
                await asyncio.sleep(0.3)  # Rate limit: don't hammer Yahoo
            except Exception as e:
                logger.warning("yfinance_ticker_failed", ticker=ticker, error=str(e))

        logger.info(
            "yfinance_scan_done",
            universe_size=len(tickers),
            batch_size=len(batch),
            tickers_scanned=len(batch),
            alerts_found=len(all_alerts),
        )
        return all_alerts

    def _load_ticker_universe(self) -> List[str]:
        file_path = Path(settings.ticker_universe_file)
        tickers: List[str] = []

        if file_path.exists():
            for raw_line in file_path.read_text().splitlines():
                line = raw_line.split("#", 1)[0].strip()
                if not line:
                    continue
                tickers.extend(part.strip() for part in line.split(",") if part.strip())
        else:
            tickers = [t.strip() for t in settings.watchlist_tickers.split(",") if t.strip()]

        seen = set()
        unique = []
        for ticker in tickers:
            normalized = ticker.upper()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)
        return unique

    def _next_ticker_batch(self, tickers: List[str], batch_size: int) -> List[str]:
        if not tickers:
            logger.warning("yfinance_universe_empty")
            return []

        safe_batch_size = max(1, min(int(batch_size or 1), len(tickers)))
        state_path = Path(settings.scan_cursor_state_file)
        state = self._read_cursor_state(state_path)
        start = int(state.get("next_index", 0) or 0) % len(tickers)
        end = start + safe_batch_size

        if end <= len(tickers):
            batch = tickers[start:end]
        else:
            batch = tickers[start:] + tickers[: end % len(tickers)]

        next_index = end % len(tickers)
        self._write_cursor_state(
            state_path,
            {
                "next_index": next_index,
                "universe_size": len(tickers),
                "batch_size": safe_batch_size,
                "last_batch_start": start,
                "last_batch_count": len(batch),
                "last_scan_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info(
            "yfinance_batch_selected",
            universe_size=len(tickers),
            batch_size=len(batch),
            start_index=start,
            next_index=next_index,
            first_ticker=batch[0] if batch else None,
            last_ticker=batch[-1] if batch else None,
        )
        return batch

    def _read_cursor_state(self, state_path: Path) -> Dict[str, Any]:
        try:
            if state_path.exists():
                return json.loads(state_path.read_text())
        except Exception as e:
            logger.warning("scan_cursor_read_failed", path=str(state_path), error=str(e))
        return {}

    def _write_cursor_state(self, state_path: Path, state: Dict[str, Any]) -> None:
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state, indent=2, sort_keys=True))
        except Exception as e:
            logger.warning("scan_cursor_write_failed", path=str(state_path), error=str(e))

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
