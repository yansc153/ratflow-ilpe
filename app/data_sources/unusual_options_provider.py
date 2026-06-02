from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.logging_config import logger


class UnusualOptionsProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def fetch_unusual_options(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def normalize_option_alert(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass
