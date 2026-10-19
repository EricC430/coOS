import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("m4_11_telemetry")


def log_zpd_event(
    event_type: str,
    user_id: str,
    role_id: str,
    challenge_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log structured telemetry event compliant with Principle I (no raw transcripts).
    [R01: ZONE 框架 §理論基礎]
    """
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "module": "M4.11",
        "event_type": event_type,
        "user_id": user_id,
        "role_id": role_id,
        "challenge_id": challenge_id,
        "details": details or {},
    }
    logger.info("[R01][M4.11] %s", json.dumps(payload, ensure_ascii=False))
