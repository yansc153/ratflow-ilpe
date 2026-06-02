#!/usr/bin/env python3
"""Update outcome tracking for cases."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import asyncio
import httpx


async def main():
    base_url = os.environ.get("RATFLOW_URL", "http://localhost:8080")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base_url}/outcomes/update")
        print(resp.json())


if __name__ == "__main__":
    asyncio.run(main())
