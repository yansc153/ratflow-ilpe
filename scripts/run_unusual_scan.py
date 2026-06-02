#!/usr/bin/env python3
"""Run public unusual options scanner."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from app.data_sources.barchart_public import BarchartPublicAdapter
from app.logging_config import logger


async def main():
    print("Running unusual options scan...")
    adapter = BarchartPublicAdapter()
    results = await adapter.fetch_unusual_options() or []
    print(f"Found {len(results)} unusual options")
    for r in results:
        print(f"  {r.get('ticker', '?')}: {r.get('option_type', '?')} {r.get('strike', '?')}")

    if not results:
        print("No results — public scraper returned empty (expected in MVP).")
        print("Use POST /alerts/options for manual alert ingestion.")


if __name__ == "__main__":
    asyncio.run(main())
