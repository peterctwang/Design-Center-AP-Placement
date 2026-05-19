"""Thread-safe in-memory task progress hub (no Celery / Redis needed).

Each long-running BackgroundTask publishes JSON messages here;
WebSocket clients subscribe by task_id to receive real-time progress.
"""
import asyncio
import uuid
from collections import defaultdict
from typing import Any


class TaskHub:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self._loops: dict[str, asyncio.AbstractEventLoop] = {}
        self._results: dict[str, Any] = {}

    def new_task_id(self) -> str:
        return uuid.uuid4().hex

    def register_loop(self, task_id: str, loop: asyncio.AbstractEventLoop) -> None:
        """Worker thread registers the main event loop so it can post messages."""
        self._loops[task_id] = loop

    def publish(self, task_id: str, message: dict) -> None:
        """Thread-safe publish from worker threads."""
        loop = self._loops.get(task_id)
        if loop is None or loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(
            self._queues[task_id].put(message), loop,
        )

    async def subscribe(self, task_id: str):
        """Async generator yielding messages until 'done' or 'error' arrives."""
        q = self._queues[task_id]
        while True:
            msg = await q.get()
            yield msg
            if msg.get("done") or msg.get("error"):
                break

    def set_result(self, task_id: str, result: Any) -> None:
        self._results[task_id] = result

    def get_result(self, task_id: str) -> Any:
        return self._results.get(task_id)

    def cleanup(self, task_id: str) -> None:
        self._queues.pop(task_id, None)
        self._loops.pop(task_id, None)


# Singleton instance
hub = TaskHub()
