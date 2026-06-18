"""M2.2 InferencePriorityQueue -- asyncio priority queue for serialized iPad calls

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.3
Priority: 1=chat (High), 2=code_diff (Medium), 3=telemetry_batch (Low)
Starvation prevention: max_wait_seconds=300 (5min) promotes low-priority tasks

anti-pattern: queue management lives on laptop FastAPI side, NOT on iPad.
iPad ai.local must remain a stateless inference-only API.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

MAX_WAIT_SECONDS = 300  # promote starved tasks after 5 minutes


@dataclass(order=True)
class InferenceTask:
    priority: int
    enqueued_at: float = field(default_factory=time.monotonic, compare=True)
    task_id: int = field(default=0, compare=True)
    payload: Any = field(default=None, compare=False)
    tag: str = field(default="", compare=False)
    # fn is the coroutine factory; called when task is dequeued
    fn: Callable[[], Coroutine[Any, Any, Any]] | None = field(default=None, compare=False)
    # future is the asyncio Future used to await the result
    future: Any = field(default=None, compare=False)


class InferencePriorityQueue:
    """Serialized asyncio priority queue for Gemma edge inference requests.

    Ensures only one inference call is in-flight to ai.local at any time.
    Starvation prevention: tasks waiting > MAX_WAIT_SECONDS are promoted to priority 0.
    """

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[InferenceTask] = asyncio.PriorityQueue()
        self._running = False

    async def put(self, task: InferenceTask) -> None:
        await self._queue.put(task)

    async def get(self) -> InferenceTask:
        """Get next task, promoting any starved low-priority tasks first."""
        # Drain queue into a temp list to re-prioritize starved tasks
        tasks: list[InferenceTask] = []
        while not self._queue.empty():
            try:
                tasks.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        now = time.monotonic()
        for t in tasks:
            if t.priority > 1 and (now - t.enqueued_at) > MAX_WAIT_SECONDS:
                t.priority = 0  # promote to highest
            await self._queue.put(t)

        return await self._queue.get()

    def qsize(self) -> int:
        return self._queue.qsize()


global_inference_queue = InferencePriorityQueue()
_task_counter = 0


async def enqueue_inference(
    priority: int,
    fn: Callable[[], Coroutine[Any, Any, Any]],
    tag: str = "",
) -> Any:
    """Helper to enqueue a task and await its completion via a Future."""
    global _task_counter
    # If the queue worker is not running (e.g., in standalone unit tests),
    # run the coroutine directly to prevent hanging.
    if not global_inference_queue._running:
        return await fn()

    _task_counter += 1
    future = asyncio.get_running_loop().create_future()
    task = InferenceTask(
        priority=priority,
        fn=fn,
        future=future,
        tag=tag,
        task_id=_task_counter,
    )
    await global_inference_queue.put(task)
    return await future

