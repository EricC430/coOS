import time
from typing import Dict, Tuple


class AchievementRateLimiter:
    """
    滑動視窗防刷機制 (M4.12.5).
    防止使用者高頻重試或腳本惡意重複刷取成就。
    預設同一個使用者針對相同特徵簽章冷卻時間為 60 秒。
    """

    def __init__(self, cooldown_seconds: float = 60.0):
        self.cooldown_seconds = cooldown_seconds
        # 鍵為 (user_id, identifier)，值為上次核准的時間戳 (float)
        self._access_records: Dict[Tuple[str, str], float] = {}

    def check_and_acquire(
        self, user_id: str, achievement_id: str, semantic_signature: str
    ) -> bool:
        now = time.time()
        key = (user_id, f"{achievement_id}:{semantic_signature}")

        last_time = self._access_records.get(key)
        if last_time is not None:
            if now - last_time < self.cooldown_seconds:
                return False

        # 通過檢查，記錄當前時間戳
        self._access_records[key] = now
        self._cleanup(now)
        return True

    def _cleanup(self, now: float):
        """定期清理過期記錄以防記憶體膨脹."""
        if len(self._access_records) > 1000:
            keys_to_delete = [
                k
                for k, ts in self._access_records.items()
                if now - ts >= self.cooldown_seconds
            ]
            for k in keys_to_delete:
                del self._access_records[k]
