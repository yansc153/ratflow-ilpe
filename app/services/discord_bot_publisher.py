import httpx
from app.config import settings
from app.logging_config import logger


class DiscordBotPublisher:
    def __init__(self):
        self.token = settings.discord_bot_token
        self.channel_id = settings.discord_channel_id
        self.base_url = "https://discord.com/api/v10"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }

    async def send_message(self, content: str, embed: dict = None) -> dict:
        url = f"{self.base_url}/channels/{self.channel_id}/messages"
        payload = {
            "content": content[:2000],
            "allowed_mentions": {"parse": []},
        }
        if embed:
            payload["embeds"] = [embed]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            logger.info("discord_message_sent", message_id=data.get("id"))
            return {"message_id": data["id"], "channel_id": data["channel_id"]}

    async def send_long_message(self, content: str) -> list[dict]:
        """Split content exceeding Discord's 2000-char limit into multiple messages."""
        results = []
        chunks = self._split_content(content, max_len=1900)
        for i, chunk in enumerate(chunks):
            prefix = f"({i + 1}/{len(chunks)})\n" if len(chunks) > 1 else ""
            payload_content = prefix + chunk
            result = await self.send_message(payload_content)
            results.append(result)
        return results

    @staticmethod
    def _split_content(content: str, max_len: int = 1900) -> list[str]:
        chunks = []
        while len(content) > max_len:
            split_at = content.rfind("\n", 0, max_len)
            if split_at == -1:
                split_at = max_len
            chunks.append(content[:split_at])
            content = content[split_at:].lstrip("\n")
        if content:
            chunks.append(content)
        return chunks

    async def test_message(self) -> dict:
        content = "🐀 **RATFLOW-ILPE** 系统测试成功！\n\n✅ 服务运行正常\n✅ Discord 连接正常\n\nThis is a test message from RATFLOW Information Leakage Prediction Engine."
        return await self.send_message(content)


discord_publisher = DiscordBotPublisher()
