#!/usr/bin/env python3
"""Send a test message to Discord using the configured bot token and channel."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from app.services.discord_bot_publisher import discord_publisher


async def main():
    print("Sending test Discord message...")
    try:
        result = await discord_publisher.test_message()
        print(f"Success! Message ID: {result['message_id']}")
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
