"""M2.1 EventDebouncer -- asyncio-based sliding window batch flusher

SPEC: docs/modules/M2_1_event_debouncing_SPEC.md v1.1 §7.1
[R08: §三.1 警報疲勞] temporal threshold prevents over-triggering M2.2
[R02: REMT §動態上下文工程] role switch forces flush before window change (RISK-M2.1-C)

Design:
- Two flush triggers: temporal threshold (role-dependent) + capacity threshold (1000)
- on_role_switched(): flush first, then update window -- order critical (RISK-M2.1-C)
- Offline buffer: failed flushes go to temp_event_queue via queue_router
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from .schema import EventBatch, RawTelemetryEvent

CAPACITY_THRESHOLD = 1000
OFFLINE_RETRY_DELAYS = [5, 15, 60]  # exponential backoff seconds (RISK-M2.1-A)

# [R08: §二 Defer-to-Breakpoint] role-specific debounce windows
ROLE_DEBOUNCE_WINDOWS: dict[str, float] = {
    "CSIE": 60.0,
    "STUDY": 60.0,
    "FAMILY": 15.0,
    "SOCIAL": 15.0,
}
DEFAULT_DEBOUNCE_WINDOW = 30.0


class EventDebouncer:
    """Asyncio sliding-window debouncer for telemetry events.

    Accepts events via push(), batches them, and delivers EventBatch to
    a downstream coroutine (flush_fn) when either threshold is hit.
    On flush failure the batch is written to temp_event_queue (SQLite)
    for arq retry.
    """

    def __init__(
        self,
        role_id: str,
        flush_fn: Callable[[EventBatch], Coroutine[Any, Any, None]],
        debounce_window: float | None = None,
        capacity: int = CAPACITY_THRESHOLD,
        db_path: str | None = None,
    ) -> None:
        self._role_id = role_id
        self._flush_fn = flush_fn
        self._window = debounce_window or ROLE_DEBOUNCE_WINDOWS.get(
            role_id, DEFAULT_DEBOUNCE_WINDOW
        )
        self._capacity = capacity
        self._db_path = db_path  # None = no offline buffer (test mode)

        self._buffer: list[RawTelemetryEvent] = []
        self._timer_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        # offline buffer state (RISK-M2.1-A)
        self._offline_buffer: list[EventBatch] = []
        self._retry_index: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def push(self, event: RawTelemetryEvent) -> None:
        """Add an event; flush immediately if capacity threshold reached."""
        async with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self._capacity:
                await self._flush_locked()
                return
            if self._timer_task is None or self._timer_task.done():
                self._timer_task = asyncio.create_task(self._timer_flush())

    async def shutdown_gracefully(self) -> None:
        """Cancel timer and force-flush remaining buffer. (RISK-M2.1-A)"""
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            await self._flush_locked()

    async def on_role_switched(self, new_role_id: str, new_window: float | None = None) -> None:
        """Flush current buffer BEFORE switching role context. (RISK-M2.1-C)

        Order: flush → update role_id → update window. Never reverse.
        """
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass
        async with self._lock:
            await self._flush_locked()
        # Now safe to change role context
        self._role_id = new_role_id
        self._window = new_window or ROLE_DEBOUNCE_WINDOWS.get(new_role_id, DEFAULT_DEBOUNCE_WINDOW)

    # ------------------------------------------------------------------
    # Introspection helpers (for tests / RISK-M2.1-A verification)
    # ------------------------------------------------------------------

    async def offline_buffer_len(self) -> int:
        return len(self._offline_buffer)

    async def next_retry_delay(self) -> float | None:
        idx = min(self._retry_index, len(OFFLINE_RETRY_DELAYS) - 1)
        return float(OFFLINE_RETRY_DELAYS[idx]) if self._offline_buffer else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _timer_flush(self) -> None:
        await asyncio.sleep(self._window)
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        """Must be called with self._lock held."""
        if not self._buffer:
            return
        batch = EventBatch(role_id=self._role_id, events=list(self._buffer))
        self._buffer.clear()
        self._timer_task = None
        try:
            await self._flush_fn(batch)
            self._retry_index = 0
        except Exception:
            # RISK-M2.1-A: downstream not reachable -- write to offline buffer
            self._offline_buffer.append(batch)
            if self._db_path:
                self._write_offline_sqlite(batch)

    def _write_offline_sqlite(self, batch: EventBatch) -> None:
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(
                "INSERT INTO temp_event_queue(id, batch_id, events_json, role_id) VALUES(?,?,?,?)",
                (
                    str(uuid.uuid4()),
                    batch.batch_id,
                    json.dumps([e.model_dump(mode="json") for e in batch.events]),
                    batch.role_id,
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # best-effort; in-memory offline_buffer is the authoritative fallback
