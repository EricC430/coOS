import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ROLE_DEFAULT_TOPICS: Dict[str, str] = {
    "role_csie": "軟體工程與分散式系統",
    "role_infra": "容器編排與網路基礎設施",
    "role_design": "使用者體驗與互動介面設計",
    "role_writing": "深度敘事與結構化寫作",
    "default": "通識技能與專案實作探索",
}

TECH_KEYWORDS = [
    "Docker", "Kubernetes", "Python", "Rust", "TypeScript", "React",
    "FastAPI", "SQLite", "PostgreSQL", "Git", "asyncio", "network",
    "bridge", "容器", "快取", "演算法", "資料庫", "前端", "後端", "API"
]

FRICTION_PATTERNS = [
    r"(?:error|exception|failed|refused|crash|timeout|bug)",
    r"(?:卡關|報錯|錯誤|失敗|無法連線|記憶體不足|找不到模組|連線被拒)",
]


@dataclass
class ExtractedContext:
    interest_topic: str
    friction_point: Optional[str]
    is_cold_start: bool
    confidence: float = 0.8


class InterestExtractor:
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session

    def extract(self, user_id: str, role_id: str) -> ExtractedContext:
        """
        Query local chat transcripts for the past 24 hours without uploading any L1 text to cloud.
        """
        if self.db is None:
            return self._cold_start(role_id)

        try:
            # Query recent chat transcripts if table exists
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            query = text(
                "SELECT content FROM chat_transcripts "
                "WHERE user_id = :user_id AND role_id = :role_id AND created_at >= :since "
                "ORDER BY created_at DESC LIMIT 50"
            )
            rows = self.db.execute(query, {"user_id": user_id, "role_id": role_id, "since": since}).fetchall()
            if not rows:
                return self._cold_start(role_id)

            combined_text = " ".join([r[0] for r in rows if r[0]])
            if not combined_text.strip():
                return self._cold_start(role_id)

            return self.analyze_text(combined_text, role_id)
        except Exception as e:
            logger.debug("Chat transcripts table not available or query failed: %s. Using cold start.", e)
            return self._cold_start(role_id)

    def analyze_text(self, text_content: Optional[str] = None, role_id: str = "default", text: Optional[str] = None) -> ExtractedContext:
        """
        Extract high-level technical focus topic and specific friction points from local text.
        """
        raw_text = text if text is not None else (text_content or "")
        found_tech = []
        for kw in TECH_KEYWORDS:
            if re.search(re.escape(kw), raw_text, re.IGNORECASE):
                found_tech.append(kw)

        found_friction = []
        for pattern in FRICTION_PATTERNS:
            matches = re.findall(pattern, raw_text, re.IGNORECASE)
            if matches:
                found_friction.extend(matches)

        topic = "、".join(found_tech[:2]) if found_tech else ROLE_DEFAULT_TOPICS.get(role_id, ROLE_DEFAULT_TOPICS["default"])
        friction = f"處理 {found_friction[0]} 疑難雜症" if found_friction else None

        return ExtractedContext(
            interest_topic=topic,
            friction_point=friction,
            is_cold_start=False,
            confidence=0.85 if found_tech else 0.6,
        )

    def _cold_start(self, role_id: str) -> ExtractedContext:
        topic = ROLE_DEFAULT_TOPICS.get(role_id, ROLE_DEFAULT_TOPICS["default"])
        return ExtractedContext(
            interest_topic=topic,
            friction_point=None,
            is_cold_start=True,
            confidence=0.5,
        )
