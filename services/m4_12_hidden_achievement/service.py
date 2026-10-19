import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from .archetypes import CORE_ARCHETYPES, ArchetypeEvalRule
from .feature_trap import FastPathMatcher, SlowPathAnalyzer, SlowPathAnalysisResult
from .models import HiddenAchievementModel, UserAchievementModel
from .schemas import (
    ArchetypeEnum,
    RarityEnum,
    UnlockEventPayload,
    UnlockedAchievementItem,
)

from .rate_limiter import AchievementRateLimiter
from .telemetry import AchievementTelemetry

logger = logging.getLogger(__name__)

RARITY_WEIGHTS = {
    RarityEnum.LEGENDARY: 3,
    RarityEnum.EPIC: 2,
    RarityEnum.RARE: 1,
}


class HiddenAchievementService:
    """
    隱藏成就主服務門面.
    負責協調快慢雙軌特徵識別、資料庫 ACID 狀態寫入、心流斷點推播與單上限 (Single Cap) 補發。
    """

    def __init__(self, db_session: Session, ws_manager=None):
        self.db = db_session
        self.ws_manager = ws_manager
        self.fast_matcher = FastPathMatcher()
        self.slow_analyzer = SlowPathAnalyzer()
        self.rate_limiter = AchievementRateLimiter(cooldown_seconds=60.0)
        self.telemetry = AchievementTelemetry()

    def is_achievement_unlocked(self, user_id: str, achievement_id: str) -> bool:
        """檢查該成就使用者是否已終身解鎖."""
        existing = (
            self.db.query(UserAchievementModel)
            .filter_by(user_id=user_id, achievement_id=achievement_id)
            .first()
        )
        return existing is not None

    async def evaluate_dialogue(
        self,
        user_id: str,
        session_id: str,
        role_id: Optional[str],
        user_message: str,
    ) -> Optional[UnlockEventPayload]:
        """
        對話評估入口:
        1. 執行快軌正則/關鍵字掃描 (<100ms)
        2. 命中候選時，執行慢軌語意解析與跳躍深度驗證
        3. 滿足條件且尚未解鎖時，原子寫入 DB 並返回解鎖 Payload
        """
        fast_results = self.fast_matcher.scan_all_archetypes(user_message)
        if not fast_results:
            return None

        for match in fast_results:
            ach_id = match.achievement_id
            if self.is_achievement_unlocked(user_id, ach_id):
                continue

            # 防刷滑動視窗檢查 (60秒冷卻)
            sig = match.matched_keywords[0] if match.matched_keywords else "default"
            if not self.rate_limiter.check_and_acquire(user_id, ach_id, sig):
                logger.info(f"[M4.12 Service] Rate limit cooldown active for user {user_id}, {ach_id}")
                continue

            rule = CORE_ARCHETYPES.get(ach_id)
            if not rule:
                continue

            # 執行慢軌語意分析
            try:
                analysis: SlowPathAnalysisResult = await self.slow_analyzer.analyze_epistemic_depth(
                    user_message, role_id=role_id
                )
            except Exception as e:
                logger.warning(f"[M4.12 Service] Slow path evaluation error: {e}")
                continue

            # 檢驗門檻
            if (
                analysis.concept_leap_depth >= rule.min_concept_leap
                and analysis.proactivity_score >= rule.min_proactivity_score
            ):
                return self._unlock_achievement(
                    user_id=user_id,
                    rule=rule,
                    role_id=role_id,
                    context_summary=f"於 {role_id or '自主探索'} 觸發: {analysis.summary}",
                )

        return None

    def _unlock_achievement(
        self,
        user_id: str,
        rule: ArchetypeEvalRule,
        role_id: Optional[str],
        context_summary: str,
    ) -> Optional[UnlockEventPayload]:
        """原子寫入成就解鎖資料與 XP 發放稽核 (ACID Guaranteed)."""
        from sqlalchemy.exc import IntegrityError

        now = datetime.now(timezone.utc)
        tx_id = f"tx_ha_{uuid.uuid4().hex[:12]}"

        user_ach = UserAchievementModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            achievement_id=rule.achievement_id,
            origin_role_id=role_id,
            unlocked_at=now,
            is_acknowledged=False,
            xp_awarded=rule.exp_reward,
            transaction_id=tx_id,
            context_summary=context_summary,
        )
        self.db.add(user_ach)
        try:
            self.db.commit()
            self.db.refresh(user_ach)
        except IntegrityError:
            self.db.rollback()
            logger.info(
                f"[M4.12 Service] Achievement {rule.achievement_id} already unlocked concurrently for user {user_id}."
            )
            return None

        # 發布結構化稽核事件 [R01]
        self.telemetry.create_unlock_audit_event(
            user_id=user_id,
            achievement_id=rule.achievement_id,
            xp_awarded=rule.exp_reward,
            transaction_id=tx_id,
            origin_role_id=role_id,
        )

        payload = UnlockEventPayload(
            event_type="HIDDEN_ACHIEVEMENT_UNLOCKED",
            achievement_id=rule.achievement_id,
            archetype=rule.archetype,
            name=rule.name,
            description=rule.description,
            flavor_text=rule.flavor_text_template,
            rarity=rule.rarity,
            exp_reward=rule.exp_reward,
            badge_icon_url=rule.badge_icon_url,
            origin_role_id=role_id,
            unlocked_at=now,
            context_summary=context_summary,
        )
        return payload

    async def handle_reconnect_catch_up(self, user_id: str) -> Optional[UnlockEventPayload]:
        """
        FR-015: 開機與重連時 Single Cap 補發機制.
        至多彈窗推播 1 筆最高稀有度的成就，其餘保留未讀狀態供畫廊標記 'NEW'。
        """
        unacked = (
            self.db.query(UserAchievementModel, HiddenAchievementModel)
            .join(HiddenAchievementModel, UserAchievementModel.achievement_id == HiddenAchievementModel.id)
            .filter(
                UserAchievementModel.user_id == user_id,
                UserAchievementModel.is_acknowledged == False,
            )
            .all()
        )

        if not unacked or not self.ws_manager:
            return None

        # 排序：稀有度最高優先，同稀有度按解鎖時間由新到舊
        def sort_key(pair):
            user_ach, ach = pair
            rarity_val = RARITY_WEIGHTS.get(RarityEnum(ach.rarity), 0)
            return (rarity_val, user_ach.unlocked_at)

        unacked.sort(key=sort_key, reverse=True)
        top_user_ach, top_ach = unacked[0]

        payload = UnlockEventPayload(
            event_type="HIDDEN_ACHIEVEMENT_UNLOCKED",
            achievement_id=top_ach.id,
            archetype=ArchetypeEnum(top_ach.archetype),
            name=top_ach.name,
            description=top_ach.description,
            flavor_text=top_user_ach.context_summary or top_ach.flavor_text_template,
            rarity=RarityEnum(top_ach.rarity),
            exp_reward=top_user_ach.xp_awarded or top_ach.exp_reward,
            badge_icon_url=top_ach.badge_icon_url,
            origin_role_id=top_user_ach.origin_role_id,
            unlocked_at=top_user_ach.unlocked_at,
            context_summary=top_user_ach.context_summary,
        )

        await self.ws_manager.broadcast_to_user(user_id, payload.model_dump(mode="json"))
        return payload

    def acknowledge_achievement(self, user_id: str, achievement_id: str) -> bool:
        """標記成就彈窗為已讀."""
        updated = (
            self.db.query(UserAchievementModel)
            .filter_by(user_id=user_id, achievement_id=achievement_id)
            .update({"is_acknowledged": True})
        )
        self.db.commit()
        return updated > 0
