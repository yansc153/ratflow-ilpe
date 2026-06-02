from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.logging_config import logger


class DataSourceBase(ABC):
    source_name: str = "base"

    @abstractmethod
    async def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        pass

    def unavailable_response(self, reason: str = "Provider unavailable") -> Dict[str, Any]:
        return {
            "source": self.source_name,
            "status": "unavailable",
            "reason": reason,
            "data": [],
        }

    def error_response(self, error: str) -> Dict[str, Any]:
        logger.error(f"{self.source_name}_error", error=error)
        return {
            "source": self.source_name,
            "status": "error",
            "error": str(error),
            "data": [],
        }
