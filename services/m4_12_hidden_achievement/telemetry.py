import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    from m0_4_logging.schema import LogEvent
except ImportError:
    # 輕量回退定義
    from pydantic import BaseModel, Field

    class LogEvent(BaseModel):
        id: str = Field(default_factory=lambda: str(uuid.uuid4()))
        timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
        module: str
        action: str
        level: str = "INFO"
        payload: Dict[str, Any] = Field(default_factory=dict)
        user_id: Optional[str] = None
        role_id: Optional[str] = None
        correlation_id: Optional[str] = None

logger = logging.getLogger(__name__)


class AchievementTelemetry:
    """
    M4.12 結構化稽核遙測與日誌發布器 (遵循 M0.4 與 [R01] 規範).
    嚴格遵循三層隱私架構：payload 內嚴禁夾帶任何 L1 對話明文或程式碼。
    """

    def create_unlock_audit_event(
        self,
        user_id: str,
        achievement_id: str,
        xp_awarded: int,
        transaction_id: str,
        origin_role_id: Optional[str] = None,
    ) -> LogEvent:
        event = LogEvent(
            module="M4.12",
            action="ACHIEVEMENT_UNLOCKED",
            level="AUDIT",
            user_id=user_id,
            role_id=origin_role_id,
            correlation_id=transaction_id,
            payload={
                "achievement_id": achievement_id,
                "xp_awarded": xp_awarded,
                "transaction_id": transaction_id,
                "r01_audit": True,
            },
        )
        logger.info(
            f"[M4.12 Telemetry] Audit event created for user {user_id}: {achievement_id} (+{xp_awarded} XP)"
        )
        return event
