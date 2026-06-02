import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Set, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import logger
from app.db import SessionLocal
from app.models import InvestigationCase, OptionAlert, LeakageReport
from app.harness.orchestrator import HarnessOrchestrator

from app.data_sources.tradier_adapter import TradierAdapter
from app.data_sources.yfinance_scanner import YFinanceScanner
from app.data_sources.barchart_csv_adapter import BarchartCSVAdapter


class ScanOrchestrator:
    def __init__(self):
        self.tradier = TradierAdapter()
        self.yfinance = YFinanceScanner()
        self.barchart = BarchartCSVAdapter()

    async def scan_all_sources(self) -> List[Dict[str, Any]]:
        logger.info("scan_all_started")
        all_alerts = []

        sources = [
            ("tradier", self.tradier),
            ("yfinance", self.yfinance),
            ("barchart_csv", self.barchart),
        ]

        for name, adapter in sources:
            try:
                alerts = await adapter.fetch_unusual_options()
                logger.info("source_scan", source=name, count=len(alerts))
                for alert in alerts:
                    alert["_source"] = name
                all_alerts.extend(alerts)
            except Exception as e:
                logger.error("source_scan_failed", source=name, error=str(e))

        deduped = self._deduplicate(all_alerts)
        filtered = self._apply_filters(deduped)
        ranked = self._rank_and_limit(filtered, limit=settings.max_alerts_per_scan)

        logger.info("scan_all_done", raw=len(all_alerts), deduped=len(deduped), filtered=len(filtered), final=len(ranked))

        if ranked:
            await self._ingest_alerts(ranked)

        return ranked

    def _deduplicate(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: Set[str] = set()
        unique = []
        for a in alerts:
            key = f"{a.get('ticker','')}:{a.get('strike','')}:{a.get('expiry','')}:{a.get('option_type','')}"
            if key not in seen:
                seen.add(key)
                unique.append(a)
        return unique

    def _apply_filters(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = []
        for a in alerts:
            volume = int(a.get("volume", 0) or 0)
            oi = int(a.get("open_interest", 0) or 0)
            last_price = float(a.get("last_price", 0) or 0)
            dte = int(a.get("dte", 0) or 0)

            if volume == 0 or oi == 0 or last_price == 0:
                continue

            vol_oi = volume / max(oi, 1)
            premium = volume * last_price * 100

            if vol_oi < 2.0:
                continue
            if premium < 20_000:
                continue
            if dte < 5 or dte > 120:
                continue

            a["_vol_oi"] = round(vol_oi, 1)
            a["_premium"] = round(premium)
            filtered.append(a)

        return filtered

    def _rank_and_limit(self, alerts: List[Dict[str, Any]], limit: int = 15) -> List[Dict[str, Any]]:
        ranked = sorted(alerts, key=lambda a: (a.get("_vol_oi", 0), a.get("_premium", 0)), reverse=True)
        return ranked[:limit]

    async def _ingest_alerts(self, alerts: List[Dict[str, Any]]):
        db = SessionLocal()
        try:
            for alert_data in alerts:
                try:
                    ticker = str(alert_data.get("ticker", "")).upper()
                    if not ticker:
                        continue

                    case = InvestigationCase(
                        ticker=ticker,
                        company_name=alert_data.get("company_name") or ticker,
                        source=alert_data.get("_source", alert_data.get("source", "scanner")),
                        status="NEW",
                    )
                    db.add(case)
                    db.flush()

                    oi = int(alert_data.get("open_interest", 0) or 0)
                    volume = int(alert_data.get("volume", 0) or 0)

                    alert = OptionAlert(
                        case_id=case.id,
                        source=alert_data.get("_source", alert_data.get("source", "scanner")),
                        ticker=ticker,
                        company_name=alert_data.get("company_name"),
                        option_type=str(alert_data.get("option_type", "CALL")).upper(),
                        strike=float(alert_data.get("strike", 0)),
                        expiry=str(alert_data.get("expiry", "")),
                        dte=int(alert_data.get("dte", 0)) if alert_data.get("dte") else None,
                        volume=volume,
                        open_interest=oi,
                        volume_oi_ratio=round(volume / oi, 2) if oi > 0 else None,
                        bid=float(alert_data.get("bid", 0)) if alert_data.get("bid") else None,
                        ask=float(alert_data.get("ask", 0)) if alert_data.get("ask") else None,
                        last_price=float(alert_data.get("last_price", 0)) if alert_data.get("last_price") else None,
                        implied_volatility=float(alert_data.get("implied_volatility", 0)) if alert_data.get("implied_volatility") else None,
                        premium=float(alert_data.get("premium", 0)) if alert_data.get("premium") else None,
                        underlying_price=float(alert_data.get("underlying_price", 0)) if alert_data.get("underlying_price") else None,
                        raw_text=alert_data.get("raw_text", ""),
                        raw_json=json.loads(json.dumps(alert_data.get("raw_json", {}), default=str)),
                        collected_at=datetime.utcnow(),
                    )
                    db.add(alert)
                    db.commit()

                    orchestrator = HarnessOrchestrator(db)
                    await orchestrator.run_case(case.id)

                    logger.info("scan_alert_ingested", case_uid=case.case_uid, ticker=ticker)
                except Exception as e:
                    logger.error("scan_alert_ingest_failed", ticker=alert_data.get("ticker", "?"), error=str(e))
                    db.rollback()
        finally:
            db.close()


scan_orchestrator = ScanOrchestrator()
