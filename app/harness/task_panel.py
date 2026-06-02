import asyncio
from typing import Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass, field
from app.logging_config import logger


@dataclass
class TaskPanel:
    parallel_tasks: List[Callable[[], Awaitable[Dict[str, Any]]]] = field(default_factory=list)
    sequential_tasks: List[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = field(default_factory=list)
    timeout_per_agent: float = 90.0
    results: Dict[str, Any] = field(default_factory=dict)

    def add_parallel(self, name: str, fn: Callable[[], Awaitable[Dict[str, Any]]]):
        self.parallel_tasks.append((name, fn))

    def add_sequential(self, name: str, fn: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        self.sequential_tasks.append((name, fn))


class TaskPanelManager:
    @staticmethod
    async def run_parallel(tasks: List[tuple], timeout: float = 90.0) -> Dict[str, Any]:
        results = {}

        async def run_one(name: str, fn):
            try:
                result = await asyncio.wait_for(fn(), timeout=timeout)
                results[name] = result
                logger.info("parallel_task_done", agent=name)
            except asyncio.TimeoutError:
                logger.error("parallel_task_timeout", agent=name)
                results[name] = {"agent_name": name, "error": "timeout"}
            except Exception as e:
                logger.error("parallel_task_failed", agent=name, error=str(e))
                results[name] = {"agent_name": name, "error": str(e)}

        await asyncio.gather(*(run_one(name, fn) for name, fn in tasks))
        return results

    @staticmethod
    async def run_sequential(tasks: List[tuple], context: Dict[str, Any], timeout: float = 90.0) -> Dict[str, Any]:
        results = {}

        for name, fn in tasks:
            try:
                result = await asyncio.wait_for(fn(context), timeout=timeout)
                results[name] = result
                context[name] = result
                logger.info("sequential_task_done", agent=name)
            except asyncio.TimeoutError:
                logger.error("sequential_task_timeout", agent=name)
                results[name] = {"agent_name": name, "error": "timeout"}
                context[name] = results[name]
            except Exception as e:
                logger.error("sequential_task_failed", agent=name, error=str(e))
                results[name] = {"agent_name": name, "error": str(e)}
                context[name] = results[name]

        return results
