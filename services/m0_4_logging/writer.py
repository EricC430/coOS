"""
M0.4 -- Log writers (sync + async)

SPEC: docs/modules/M0_4_structured_logging_SPEC.md

LogWriter      -- synchronous, for scripts / migrations / tests
AsyncLogWriter -- async fire-and-forget, for FastAPI request path
get_logger()   -- module-level singleton accessor
"""
import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from .schema import LogEvent

# Default DB path (relative to project root); callers may override.
_DEFAULT_DB = (
    Path(__file__).resolve().parents[2] / "data" / "coos_local.db"
)

# Python stdlib logger for stdout (dev mode dual-write)
_stdout_logger = logging.getLogger("coOS.m0_4")
if not _stdout_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
    )
    _stdout_logger.addHandler(_handler)
    _stdout_logger.setLevel(logging.DEBUG)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS raw_tracking_logs (
    id             TEXT PRIMARY KEY,
    timestamp      TEXT NOT NULL,
    module         TEXT NOT NULL,
    action         TEXT NOT NULL,
    level          TEXT NOT NULL DEFAULT 'INFO',
    payload        TEXT NOT NULL,
    user_id        TEXT,
    role_id        TEXT,
    correlation_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_rtl_module      ON raw_tracking_logs(module);
CREATE INDEX IF NOT EXISTS idx_rtl_timestamp   ON raw_tracking_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_rtl_correlation ON raw_tracking_logs(correlation_id);
"""

_INSERT_SQL = """
INSERT INTO raw_tracking_logs
    (id, timestamp, module, action, level, payload, user_id, role_id, correlation_id)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


class LogWriter:
    """Synchronous log writer for tests, scripts, and migration helpers."""

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or str(_DEFAULT_DB)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_table(self) -> None:
        with self._connect() as conn:
            conn.executescript(_CREATE_TABLE_SQL)

    def write(
        self,
        module: str,
        action: str,
        level: str = "INFO",
        payload: dict[str, Any] | None = None,
        user_id: str | None = None,
        role_id: str | None = None,
        correlation_id: str | None = None,
        event_id: str | None = None,
    ) -> str:
        kwargs = {}
        if event_id:
            kwargs["id"] = event_id
        event = LogEvent(
            module=module,
            action=action,
            level=level,
            payload=payload or {},
            user_id=user_id,
            role_id=role_id,
            correlation_id=correlation_id,
            **kwargs
        )
        with self._connect() as conn:
            conn.execute(
                _INSERT_SQL,
                (
                    event.id,
                    event.timestamp.isoformat(),
                    event.module,
                    event.action,
                    event.level,
                    json.dumps(event.payload, ensure_ascii=False),
                    event.user_id,
                    event.role_id,
                    event.correlation_id,
                ),
            )
        return event.id

    def query_all(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM raw_tracking_logs ORDER BY timestamp"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def query_by_module(self, module: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM raw_tracking_logs WHERE module = ? ORDER BY timestamp",
                (module,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]


class AsyncLogWriter:
    """
    Async fire-and-forget log writer for FastAPI request path.

    Usage:
        writer = AsyncLogWriter(db_path="...")
        await writer.start()          # start background flush worker
        await writer.emit(...)        # fire-and-forget
        await writer.stop()           # graceful shutdown
    """

    def __init__(
        self,
        db_path: str | None = None,
        batch_size: int = 50,
        flush_interval_s: float = 2.0,
        dev_mode: bool = False,
    ) -> None:
        self._db_path = db_path or str(_DEFAULT_DB)
        self._batch_size = batch_size
        self._flush_interval = flush_interval_s
        self._dev_mode = dev_mode
        self._queue: asyncio.Queue[LogEvent] = asyncio.Queue(maxsize=10000)
        self._worker_task: asyncio.Task | None = None
        self._sync_writer = LogWriter(db_path=self._db_path)

    async def start(self) -> None:
        """Initialise table and launch background flush worker."""
        self._sync_writer.init_table()
        self._worker_task = asyncio.create_task(self._flush_worker())

    async def stop(self) -> None:
        """Flush remaining events and cancel worker."""
        if self._worker_task:
            # Drain queue
            await self._drain()
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def emit(
        self,
        module: str,
        action: str,
        level: str = "INFO",
        payload: dict[str, Any] | None = None,
        user_id: str | None = None,
        role_id: str | None = None,
        correlation_id: str | None = None,
        event_id: str | None = None,
    ) -> None:
        """Fire-and-forget: enqueue and return immediately."""
        kwargs = {}
        if event_id:
            kwargs["id"] = event_id
        event = LogEvent(
            module=module,
            action=action,
            level=level,
            payload=payload or {},
            user_id=user_id,
            role_id=role_id,
            correlation_id=correlation_id,
            **kwargs
        )
        if self._dev_mode:
            _stdout_logger.log(
                logging.getLevelName(event.level if event.level != "AUDIT" else "WARNING"),
                "%s %s %s",
                event.module,
                event.action,
                event.payload,
            )
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop DEBUG on overflow; ERROR/AUDIT are force-inserted by waiting
            if event.level in ("ERROR", "AUDIT"):
                await self._queue.put(event)

    async def _flush_worker(self) -> None:
        while True:
            batch: list[LogEvent] = []
            try:
                while len(batch) < self._batch_size:
                    event = await asyncio.wait_for(
                        self._queue.get(), timeout=self._flush_interval
                    )
                    batch.append(event)
            except TimeoutError:
                pass
            if batch:
                await self._write_batch(batch)

    async def _drain(self) -> None:
        batch: list[LogEvent] = []
        while not self._queue.empty():
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if batch:
            await self._write_batch(batch)

    async def _write_batch(self, batch: list[LogEvent]) -> None:
        # Run blocking SQLite in default executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_write_batch, batch)

    def _sync_write_batch(self, batch: list[LogEvent]) -> None:
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        try:
            conn.executemany(
                _INSERT_SQL,
                [
                    (
                        e.id,
                        e.timestamp.isoformat(),
                        e.module,
                        e.action,
                        e.level,
                        json.dumps(e.payload, ensure_ascii=False),
                        e.user_id,
                        e.role_id,
                        e.correlation_id,
                    )
                    for e in batch
                ],
            )
            conn.commit()
        finally:
            conn.close()


# Module-level singleton (initialised lazily)
_singleton: AsyncLogWriter | None = None


def get_logger(db_path: str | None = None, dev_mode: bool = False) -> AsyncLogWriter:
    """Return the module-level AsyncLogWriter singleton."""
    global _singleton
    if _singleton is None:
        _singleton = AsyncLogWriter(db_path=db_path, dev_mode=dev_mode)
    return _singleton
