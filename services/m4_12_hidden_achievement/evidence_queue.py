import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .models import EpistemicEvidenceQueueModel
from .feature_trap import SlowPathAnalyzer, SlowPathAnalysisResult

logger = logging.getLogger(__name__)


class EvidenceQueueManager:
    """
    離線特徵佐證暫存佇列管理器.
    負責在本地 Gemma 離線或逾時 (>3s) 時持久化至 epistemic_evidence_queue，
    並於系統連線/閒置時自動排程補算。
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    async def enqueue_if_timeout_or_offline(
        self,
        session_id: str,
        user_id: str,
        origin_role_id: Optional[str],
        source_type: str,
        raw_excerpt: str,
        analyzer: SlowPathAnalyzer,
    ) -> Optional[EpistemicEvidenceQueueModel]:
        try:
            # 嘗試在逾時門限內執行慢軌推論
            analysis: SlowPathAnalysisResult = await analyzer.analyze_epistemic_depth(
                raw_excerpt, role_id=origin_role_id
            )
            # 若順利完成推論，無須排入離線佇列
            return None
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning(
                f"[M4.12 EvidenceQueue] Fallback triggered due to error/timeout: {exc}. Enqueuing excerpt."
            )
            queue_item = EpistemicEvidenceQueueModel(
                id=str(uuid.uuid4()),
                session_id=session_id,
                user_id=user_id,
                origin_role_id=origin_role_id,
                source_type=source_type,
                raw_excerpt=raw_excerpt,
                status="PENDING",
                retry_count=0,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(queue_item)
            self.db.commit()
            self.db.refresh(queue_item)
            return queue_item

    async def process_pending_items(
        self,
        analyzer: SlowPathAnalyzer,
        batch_size: int = 10,
    ) -> int:
        """
        守護排程器：出隊並重試補算積壓的特徵佐證.
        """
        pending_items = (
            self.db.query(EpistemicEvidenceQueueModel)
            .filter(EpistemicEvidenceQueueModel.status == "PENDING")
            .order_by(EpistemicEvidenceQueueModel.created_at.asc())
            .limit(batch_size)
            .all()
        )

        processed_count = 0
        for item in pending_items:
            item.status = "PROCESSING"
            self.db.commit()

            try:
                result = await analyzer.analyze_epistemic_depth(
                    item.raw_excerpt, role_id=item.origin_role_id
                )
                item.concept_leap_depth = result.concept_leap_depth
                item.proactivity_score = result.proactivity_score
                item.extracted_themes_json = json.dumps(result.themes, ensure_ascii=False)
                item.status = "EVALUATED"
                item.processed_at = datetime.now(timezone.utc)
                self.db.commit()
                processed_count += 1
            except Exception as e:
                logger.error(f"[M4.12 EvidenceQueue] Failed to process item {item.id}: {e}")
                item.retry_count += 1
                if item.retry_count >= 3:
                    item.status = "FAILED"
                else:
                    item.status = "PENDING"
                self.db.commit()

        return processed_count
