import threading
import time
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter to prevent compulsive gambling / addiction (FR-006).
    Enforces maximum `max_requests` per `window_seconds`.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        # key: (user_id, role_id) -> deque of timestamp floats
        self._records: Dict[Tuple[str, str], deque[float]] = defaultdict(deque)

    def is_allowed(self, user_id: str, role_id: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        with self._lock:
            now = time.time()
            key = (user_id, role_id)
            queue = self._records[key]

            # Evict timestamps outside sliding window
            while queue and queue[0] <= now - self.window_seconds:
                queue.popleft()

            if len(queue) >= self.max_requests:
                oldest = queue[0]
                retry_after = int(self.window_seconds - (now - oldest))
                return False, max(1, retry_after)

            queue.append(now)
            return True, 0

    def reset(self, user_id: Optional[str] = None, role_id: Optional[str] = None) -> None:
        with self._lock:
            if user_id and role_id:
                self._records.pop((user_id, role_id), None)
            else:
                self._records.clear()
