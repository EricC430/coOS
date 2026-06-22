"""
M4.13 — Community SSE Event Broker

SPEC: docs/modules/M3_7_community_ui_SPEC.md §7.4 (SSE stream)
Community-scoped: only pushes events to subscribers of the same community_id.
Event types: POST_PUBLISHED, COMMITMENT_VALIDATED, CHALLENGE_ACTIVATED
"""
import asyncio
import json
import logging
from collections import defaultdict
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# In-memory subscriber registry: community_id → set of asyncio.Queue
_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)


async def subscribe(community_id: str) -> AsyncGenerator[str, None]:
    """
    Yield SSE-formatted events for a given community.
    The caller should use this as an async generator in a StreamingResponse.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=64)
    _subscribers[community_id].add(queue)
    logger.info(f"[M4.13 SSE] New subscriber for community {community_id}")

    try:
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _subscribers[community_id].discard(queue)
        logger.info(f"[M4.13 SSE] Subscriber left community {community_id}")


async def broadcast(community_id: str, event: dict) -> int:
    """
    Broadcast an event to all subscribers of a community.
    Returns the number of subscribers notified.
    """
    queues = _subscribers.get(community_id, set())
    notified = 0
    dead_queues = []

    for queue in queues:
        try:
            queue.put_nowait(event)
            notified += 1
        except asyncio.QueueFull:
            dead_queues.append(queue)
            logger.warning(f"[M4.13 SSE] Dropping slow subscriber for community {community_id}")

    # Clean up dead queues
    for q in dead_queues:
        _subscribers[community_id].discard(q)

    return notified


def get_subscriber_count(community_id: str) -> int:
    """Get the number of active subscribers for a community."""
    return len(_subscribers.get(community_id, set()))
