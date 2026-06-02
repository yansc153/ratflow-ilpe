import asyncio
import json
import re
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from app.config import settings
from app.logging_config import logger


class DeepSeekClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=float(settings.llm_timeout_seconds),
        )

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_json: bool = True,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        model = model or settings.deepseek_fast_model
        temperature = temperature if temperature is not None else settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        extra = {}
        if use_json:
            extra["response_format"] = {"type": "json_object"}

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **extra,
                )
                content = response.choices[0].message.content.strip()
                if use_json:
                    return self._safe_parse_json(content)
                return {"text": content}
            except Exception as e:
                last_error = str(e)
                logger.warning("deepseek_retry", attempt=attempt + 1, error=last_error)
                if attempt < max_retries:
                    await asyncio.sleep(1.5 ** attempt)
                continue

        logger.error("deepseek_all_retries_failed", error=last_error)
        raise RuntimeError(f"DeepSeek API failed after {max_retries + 1} attempts: {last_error}")

    @staticmethod
    def _safe_parse_json(content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        logger.error("json_parse_failed", content_preview=content[:200])
        raise ValueError(f"Could not parse JSON from response: {content[:200]}...")


deepseek = DeepSeekClient()
