"""M2.2 Concurrency and Queue Serialization Integration Test"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch

from m2_2_gemma.queue import global_inference_queue, enqueue_inference

@pytest.fixture(autouse=True)
def clean_queue():
    global_inference_queue._running = False
    global_inference_queue._queue = asyncio.PriorityQueue()
    yield
    global_inference_queue._running = False
    global_inference_queue._queue = asyncio.PriorityQueue()

@pytest.mark.asyncio
async def test_inference_concurrency_serialization():
    """Verify that multiple concurrent requests are serialized by the queue worker

    and processed in priority order.
    """
    execution_log = []

    # A mock async function representing the actual HTTP request
    async def mock_request(name: str, delay: float):
        execution_log.append(f"start:{name}")
        await asyncio.sleep(delay)
        execution_log.append(f"end:{name}")
        return f"result:{name}"

    # Start the worker task
    global_inference_queue._running = True
    worker_running = True

    async def dummy_worker():
        while worker_running:
            try:
                task = await global_inference_queue.get()
                if task.fn is None:
                    continue
                try:
                    res = await task.fn()
                    if task.future and not task.future.done():
                        task.future.set_result(res)
                except Exception as exc:
                    if task.future and not task.future.done():
                        task.future.set_exception(exc)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    # First, let's enqueue tasks while worker is NOT running to fill the queue
    # Task 1: Priority 3 (Low)
    # Task 2: Priority 3 (Low)
    # Task 3: Priority 1 (High)
    fut1 = asyncio.create_task(enqueue_inference(priority=3, fn=lambda: mock_request("task1", 0.02), tag="task1"))
    fut2 = asyncio.create_task(enqueue_inference(priority=3, fn=lambda: mock_request("task2", 0.02), tag="task2"))
    fut3 = asyncio.create_task(enqueue_inference(priority=1, fn=lambda: mock_request("task3", 0.02), tag="task3"))

    # Let event loop enqueue them
    await asyncio.sleep(0.01)

    # Start the worker now
    worker_task = asyncio.create_task(dummy_worker())

    try:
        # Wait for all tasks to complete
        results = await asyncio.gather(fut1, fut2, fut3)

        assert results == ["result:task1", "result:task2", "result:task3"]

        # The worker should pull task3 first because it has priority 1,
        # then task1 and task2 (priority 3).
        assert execution_log[0] == "start:task3"
        assert execution_log[1] == "end:task3"
        assert execution_log[2] == "start:task1"
        assert execution_log[3] == "end:task1"
        assert execution_log[4] == "start:task2"
        assert execution_log[5] == "end:task2"

    finally:
        worker_running = False
        worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)
        global_inference_queue._running = False


@pytest.mark.asyncio
async def test_inference_cancellation_and_timeout():
    """Verify that cancelled tasks are discarded by the worker."""
    execution_log = []

    async def mock_request(name: str):
        execution_log.append(name)
        return "ok"

    global_inference_queue._running = True
    
    # Enqueue task1 and task2
    fut1 = asyncio.create_task(enqueue_inference(priority=3, fn=lambda: mock_request("task1"), tag="task1"))
    fut2 = asyncio.create_task(enqueue_inference(priority=3, fn=lambda: mock_request("task2"), tag="task2"))

    # Let event loop enqueue them
    await asyncio.sleep(0.01)

    # Cancel task2 before worker starts
    fut2.cancel()

    # Worker with cancellation check (replicating the implementation in main.py)
    worker_running = True
    async def dummy_worker():
        while worker_running:
            try:
                task = await global_inference_queue.get()
                if task.future and task.future.cancelled():
                    continue
                try:
                    res = await task.fn()
                    if task.future and not task.future.done():
                        task.future.set_result(res)
                except Exception as exc:
                    if task.future and not task.future.done():
                        task.future.set_exception(exc)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    worker_task = asyncio.create_task(dummy_worker())

    try:
        # Wait for task1
        res1 = await fut1
        assert res1 == "ok"
        
        # task2 is cancelled, so awaiting it raises CancelledError
        with pytest.raises(asyncio.CancelledError):
            await fut2

        # Verify that task2 was NEVER executed
        assert "task1" in execution_log
        assert "task2" not in execution_log

    finally:
        worker_running = False
        worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)
        global_inference_queue._running = False


@pytest.mark.asyncio
async def test_drift_shield_timeout_fail_open():
    """Verify that DriftShield._semantic_audit fails open on timeout."""
    from m2_3_eguard.drift import DriftShield

    # Mock DriftShield's ai_local_host so it tries semantic audit
    shield = DriftShield(ai_local_host="http://localhost:11434")

    # Mock enqueue_inference to simulate a timeout delay
    async def mock_enqueue_inference(*args, **kwargs):
        await asyncio.sleep(1.0)
        return True

    with patch("m2_2_gemma.queue.enqueue_inference", side_effect=mock_enqueue_inference):
        with patch("m2_3_eguard.drift.asyncio.wait_for", side_effect=asyncio.TimeoutError):
            res = await shield._semantic_audit("hello injection attempt")
            # Should fail open and return False instead of raising exception
            assert res is False

