"""M2.1 EventDebouncer 驗收測試

SPEC: docs/modules/M2_1_event_debouncing_SPEC.md v1.1 §6
[R08: §三.1 警報疲勞] debounce mechanism prevents model over-triggering
[R02: REMT §動態上下文工程] role switch flush prevents cross-role batch contamination

Acceptance criteria:
  1. debouncing_and_batching -- events within window batched into one
  2. queue_overflow_limit    -- capacity threshold triggers immediate flush
  3. graceful_flush_on_shutdown -- remaining events flushed on shutdown
  4. role_switch_forces_flush -- RISK-M2.1-C: old batch flushed before new role
  5. offline_exponential_backoff -- RISK-M2.1-A: failed flush queued with retry delay
"""

import asyncio
import os
import subprocess
import sqlite3
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "services"

import sys
sys.path.insert(0, str(SERVICES_DIR))

from m2_1_event_debouncer.debouncer import EventDebouncer, OFFLINE_RETRY_DELAYS
from m2_1_event_debouncer.schema import EventBatch, RawTelemetryEvent


def make_event(event_type: str = "keystroke", data: str = "k") -> RawTelemetryEvent:
    return RawTelemetryEvent(event_type=event_type, module="M1.1.2", data={"key": data})


# ---------------------------------------------------------------------------
# 驗收條件 1: 時間門檻內的高頻事件打包為單一批次
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_debouncing_and_batching():
    """AC1: events within debounce window are batched into a single EventBatch"""
    received: list[EventBatch] = []

    async def flush_fn(batch: EventBatch) -> None:
        received.append(batch)

    debouncer = EventDebouncer(
        role_id="CSIE",
        flush_fn=flush_fn,
        debounce_window=0.1,  # 100ms for speed
        capacity=1000,
    )

    for i in range(10):
        await debouncer.push(make_event(data=f"k{i}"))

    await asyncio.sleep(0.15)

    assert len(received) == 1
    assert received[0].size == 10
    assert received[0].role_id == "CSIE"
    assert all(e.event_type == "keystroke" for e in received[0].events)


# ---------------------------------------------------------------------------
# 驗收條件 2: 容量門檻觸發立即 flush
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_queue_overflow_limit():
    """AC2: reaching capacity threshold triggers immediate flush without waiting for timer"""
    received: list[EventBatch] = []

    async def flush_fn(batch: EventBatch) -> None:
        received.append(batch)

    debouncer = EventDebouncer(
        role_id="CSIE",
        flush_fn=flush_fn,
        debounce_window=60.0,  # long window -- should NOT be the trigger
        capacity=5,
    )

    for i in range(5):
        await debouncer.push(make_event(data=f"pos_{i}"))

    # No sleep needed -- capacity flush is synchronous within push()
    await asyncio.sleep(0)

    assert len(received) == 1
    assert received[0].size == 5


# ---------------------------------------------------------------------------
# 驗收條件 3: shutdown 強制 flush 剩餘 buffer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_graceful_flush_on_shutdown():
    """AC3: shutdown_gracefully() flushes remaining buffer even before timer"""
    received: list[EventBatch] = []

    async def flush_fn(batch: EventBatch) -> None:
        received.append(batch)

    debouncer = EventDebouncer(
        role_id="FAMILY",
        flush_fn=flush_fn,
        debounce_window=60.0,
        capacity=1000,
    )

    await debouncer.push(make_event(event_type="focus_change", data="vscode"))
    assert len(received) == 0  # not yet flushed

    await debouncer.shutdown_gracefully()

    assert len(received) == 1
    assert received[0].size == 1
    assert received[0].events[0].data["key"] == "vscode"


# ---------------------------------------------------------------------------
# 驗收條件 4: RISK-M2.1-C 角色切換強制 flush 舊批次
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_role_switch_forces_flush():
    """AC4 (RISK-M2.1-C): ROLE_SWITCHED flushes old role's buffer before new context"""
    received: list[EventBatch] = []

    async def flush_fn(batch: EventBatch) -> None:
        received.append(batch)

    debouncer = EventDebouncer(
        role_id="CSIE",
        flush_fn=flush_fn,
        debounce_window=60.0,
        capacity=1000,
    )

    await debouncer.push(make_event(data="csie_event"))
    assert len(received) == 0

    # Switch role -- must flush CSIE batch first
    await debouncer.on_role_switched("FAMILY")

    assert len(received) == 1, "CSIE batch should have been flushed on role switch"
    old_batch = received[0]
    assert old_batch.role_id == "CSIE"
    assert old_batch.events[0].data["key"] == "csie_event"

    # New events belong to FAMILY role
    await debouncer.push(make_event(event_type="focus_change", data="family_event"))
    await debouncer.shutdown_gracefully()

    assert len(received) == 2
    new_batch = received[1]
    assert new_batch.role_id == "FAMILY"
    assert new_batch.events[0].data["key"] == "family_event"


# ---------------------------------------------------------------------------
# 驗收條件 5: RISK-M2.1-A 離線指數退避
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_offline_exponential_backoff():
    """AC5 (RISK-M2.1-A): failed flush writes to offline buffer with exponential backoff"""
    flush_call_count = 0

    async def failing_flush_fn(batch: EventBatch) -> None:
        nonlocal flush_call_count
        flush_call_count += 1
        raise ConnectionError("M2.2 not reachable")

    debouncer = EventDebouncer(
        role_id="CSIE",
        flush_fn=failing_flush_fn,
        debounce_window=0.05,
        capacity=1000,
    )

    await debouncer.push(make_event(data="k1"))
    await asyncio.sleep(0.1)  # let timer fire

    # Batch should be in offline buffer
    offline_len = await debouncer.offline_buffer_len()
    assert offline_len > 0, "failed batch should be in offline buffer"

    # First retry delay should be 5s
    next_delay = await debouncer.next_retry_delay()
    assert next_delay == float(OFFLINE_RETRY_DELAYS[0]), (
        f"first retry delay should be {OFFLINE_RETRY_DELAYS[0]}s"
    )


# ---------------------------------------------------------------------------
# 驗收條件 5b: 離線 buffer 寫入 SQLite temp_event_queue (with real DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_offline_writes_to_sqlite(tmp_path):
    """AC5b: offline batch is persisted to temp_event_queue in SQLite"""
    db_path = tmp_path / "test.db"
    env = {**os.environ, "LOCAL_DB_PATH": str(db_path)}
    result = subprocess.run(
        ["uv", "run", "alembic", "-c", "alembic_local.ini", "upgrade", "head"],
        cwd=str(SERVICES_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    async def failing_flush_fn(batch: EventBatch) -> None:
        raise ConnectionError("M2.2 not reachable")

    debouncer = EventDebouncer(
        role_id="CSIE",
        flush_fn=failing_flush_fn,
        debounce_window=0.05,
        capacity=1000,
        db_path=str(db_path),
    )

    await debouncer.push(make_event(data="offline_k"))
    await asyncio.sleep(0.1)

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT * FROM temp_event_queue").fetchall()
    conn.close()

    assert len(rows) >= 1, "offline batch must be written to temp_event_queue"
