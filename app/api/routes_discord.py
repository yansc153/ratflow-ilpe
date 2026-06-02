from fastapi import APIRouter
from app.schemas import DiscordTestResponse
from app.services.discord_bot_publisher import discord_publisher
from app.logging_config import logger

router = APIRouter(prefix="/discord", tags=["discord"])


@router.post("/test", response_model=DiscordTestResponse)
async def test_discord():
    try:
        result = await discord_publisher.test_message()
        return DiscordTestResponse(success=True, message_id=result.get("message_id"))
    except Exception as e:
        logger.error("discord_test_failed", error=str(e))
        return DiscordTestResponse(success=False, error=str(e))
