#!/usr/bin/env python3
"""Import option alerts from a CSV file."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import csv
import asyncio
import httpx


async def main():
    if len(sys.argv) < 2:
        print("Usage: python import_csv_alerts.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]
    base_url = os.environ.get("RATFLOW_URL", "http://localhost:8080")

    alerts = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alerts.append({
                "source": row.get("source", "csv_import"),
                "ticker": row.get("ticker", ""),
                "option_type": row.get("option_type", "CALL"),
                "strike": float(row.get("strike", 0)),
                "expiry": row.get("expiry", ""),
                "dte": int(row.get("dte", 0)) if row.get("dte") else None,
                "volume": int(row.get("volume", 0)),
                "open_interest": int(row.get("open_interest", 0)),
                "bid": float(row.get("bid", 0)) if row.get("bid") else None,
                "ask": float(row.get("ask", 0)) if row.get("ask") else None,
                "last_price": float(row.get("last_price", 0)) if row.get("last_price") else None,
                "implied_volatility": float(row.get("implied_volatility", 0)) if row.get("implied_volatility") else None,
                "premium": float(row.get("premium", 0)) if row.get("premium") else None,
                "underlying_price": float(row.get("underlying_price", 0)) if row.get("underlying_price") else None,
                "raw_text": row.get("raw_text", ""),
            })

    print(f"Importing {len(alerts)} alerts...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, alert in enumerate(alerts):
            resp = await client.post(f"{base_url}/alerts/options", json=alert)
            if resp.status_code == 200:
                data = resp.json()
                print(f"  [{i+1}/{len(alerts)}] Created case {data['case_uid']} for {alert['ticker']}")
            else:
                print(f"  [{i+1}/{len(alerts)}] Failed: {resp.status_code} {resp.text}")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
