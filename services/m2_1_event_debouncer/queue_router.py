"""M2.1 arq task: retry flushing offline-buffered EventBatches to M2.2

SPEC: docs/modules/M2_1_event_debouncing_SPEC.md v1.1 §7.3 (異常處理)
RISK-M2.1-A mitigation: exponential backoff 5s -> 15s -> 60s

This module defines the arq worker function. In production it is registered
with an arq WorkerSettings and run alongside the FastAPI sidecar.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

RETRY_DELAYS = [5, 15, 60]  # seconds


async def retry_offline_batches(ctx: dict[str, Any]) -> int:
    """arq task: read pending rows from temp_event_queue, attempt delivery to M2.2.

    Returns the number of batches successfully flushed.
    """
    import asyncio
    db_path: str = ctx.get("db_path", "../data/coos.db")
    m2_2_flush_fn = ctx.get("m2_2_flush_fn")  # injected by worker startup
    if m2_2_flush_fn is None:
        return 0

    lock = None
    try:
        import main as _main
        lock = getattr(_main, "_sqlite_lock", None)
    except Exception:
        pass

    def _fetch():
        if lock is not None:
            lock.acquire()
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            now = datetime.now(UTC).isoformat()
            rows = conn.execute(
                "SELECT * FROM temp_event_queue WHERE next_retry_at IS NULL OR next_retry_at <= ? LIMIT 50",
                (now,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        finally:
            if lock is not None:
                lock.release()

    rows = await asyncio.to_thread(_fetch)

    flushed = 0
    deletes = []
    updates = []

    for row in rows:
        try:
            events_data = json.loads(row["events_json"])
            await m2_2_flush_fn(row["batch_id"], events_data, row["role_id"])
            deletes.append(row["id"])
            flushed += 1
        except Exception:
            retry_count = row["retry_count"] + 1
            delay_idx = min(retry_count - 1, len(RETRY_DELAYS) - 1)
            next_retry = (
                datetime.now(UTC) + timedelta(seconds=RETRY_DELAYS[delay_idx])
            ).isoformat()
            updates.append((retry_count, next_retry, row["id"]))

    def _apply_changes():
        if not deletes and not updates:
            return
        if lock is not None:
            lock.acquire()
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            conn.execute("PRAGMA foreign_keys=ON")
            if deletes:
                conn.executemany("DELETE FROM temp_event_queue WHERE id = ?", [(d,) for d in deletes])
            if updates:
                conn.executemany("UPDATE temp_event_queue SET retry_count = ?, next_retry_at = ? WHERE id = ?", updates)
            conn.commit()
            conn.close()
        finally:
            if lock is not None:
                lock.release()

    await asyncio.to_thread(_apply_changes)
    return flushed
