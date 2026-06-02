#!/usr/bin/env python3
"""Seed a mock option alert and run the full harness end-to-end."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import httpx


MOCK_ALERT = {
    "source": "manual_mock",
    "ticker": "RZLV",
    "company_name": "RZLV Inc.",
    "option_type": "CALL",
    "strike": 4.0,
    "expiry": "2026-07-17",
    "dte": 49,
    "volume": 9391,
    "open_interest": 6243,
    "bid": 0.18,
    "ask": 0.20,
    "last_price": 0.19,
    "implied_volatility": 1.25,
    "iv_change": 0.12,
    "premium": 182000,
    "underlying_price": 2.95,
    "underlying_move_5d": 0.02,
    "raw_text": "Mock unusual call alert for end-to-end harness test",
}


async def main():
    base_url = os.environ.get("RATFLOW_URL", "http://localhost:8080")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Health check
        print("1. Checking health...")
        resp = await client.get(f"{base_url}/health")
        print(f"   Health: {resp.json()}")

        # Submit alert
        print("2. Submitting mock alert...")
        resp = await client.post(f"{base_url}/alerts/options", json=MOCK_ALERT)
        case = resp.json()
        print(f"   Case created: {case['case_uid']} (id={case['id']})")

        # Wait for harness
        print("3. Waiting for harness to complete (this may take 60-120s)...")
        print("   The harness runs in the background. Check logs at /cases/{id}")
        for i in range(24):
            await asyncio.sleep(5)
            resp = await client.get(f"{base_url}/cases/{case['id']}")
            data = resp.json()
            status = data.get("status", "UNKNOWN")
            print(f"   Status: {status}")
            if status in ("OI_CONFIRMATION_PENDING", "PUBLISHED", "PUBLISH_SKIPPED", "PUBLISH_RETRY_PENDING", "PUBLISH_FAILED", "DISCORD_SENT", "CLOSED"):
                print(f"   Harness complete!")
                print(f"   Leakage Score: {data.get('leakage_report', {})}")
                break

        # Check reports
        print("4. Checking reports...")
        resp = await client.get(f"{base_url}/reports/recent?limit=5")
        reports = resp.json()
        print(f"   Recent reports: {len(reports)}")
        for r in reports:
            print(f"   - Case {r['case_id']}: Leakage={r['leakage_score']}, Discord={r['discord_message_id']}")

        print("\nDone! Check Discord for the report if leakage_score >= 65.")


if __name__ == "__main__":
    asyncio.run(main())
