import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import RoleSkillMastery, ZPDChallenge
from .rate_limiter import SlidingWindowRateLimiter
from .schemas import (
    ChallengeStatus,
    CompleteChallengeResponse,
    TaskDifficulty,
    TaskType,
    ZPDChallengeDTO,
)
from .task_synthesizer import TaskSynthesizer
from .telemetry import log_zpd_event

logger = logging.getLogger(__name__)

# Global rate limiter instance for anti-addiction protection
_global_rate_limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=3600)


class ZPDPipelineService:
    def __init__(
        self,
        db_session: Session,
        synthesizer: Optional[TaskSynthesizer] = None,
        rate_limiter: Optional[SlidingWindowRateLimiter] = None,
    ):
        self.db = db_session
        self.synthesizer = synthesizer or TaskSynthesizer()
        self.rate_limiter = rate_limiter or _global_rate_limiter

    def draw_challenge(
        self,
        user_id: str,
        role_id: str,
        force_fallback: bool = False,
        preferred_task_type: Optional[TaskType] = None,
        preferred_difficulty: Optional[TaskDifficulty] = None,
        context_vars: Optional[Dict[str, Any]] = None,
    ) -> ZPDChallengeDTO:
        """
        Draw a new ZPD challenge adhering to single-slot and rate limiting rules.
        """
        allowed, retry_after = self.rate_limiter.is_allowed(user_id=user_id, role_id=role_id)
        if not allowed:
            log_zpd_event("rate_limit_exceeded", user_id, role_id, details={"retry_after": retry_after})
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"抽卡過於頻繁，請於 {retry_after} 秒後再試（防沉迷保護機制）",
                headers={"Retry-After": str(retry_after)},
            )

        # Extract recent context and friction points if not explicitly provided
        if context_vars is None:
            from .interest_extractor import InterestExtractor
            extractor = InterestExtractor(self.db)
            extracted = extractor.extract(user_id=user_id, role_id=role_id)
            context_vars = {
                "interest_topic": extracted.interest_topic,
                "friction_point": extracted.friction_point,
            }

        # Query current mastery
        mastery = (
            self.db.query(RoleSkillMastery)
            .filter_by(user_id=user_id, role_id=role_id)
            .first()
        )
        current_p = mastery.p_mastery if mastery else 0.30

        # Sample task type and difficulty using ZONE framework
        from .zone_sampler import ZoneSampler
        sampler = ZoneSampler()
        decision = sampler.sample(
            p_mastery=current_p,
            force_task_type=preferred_task_type,
        )

        # Synthesize task (offline fallback or dynamic)
        task_data = self.synthesizer.synthesize_fallback(
            user_id=user_id,
            role_id=role_id,
            preferred_task_type=preferred_task_type or decision.task_type,
            preferred_difficulty=preferred_difficulty or decision.difficulty,
            context_vars=context_vars,
        )

        task_data["zpd_zone"] = decision.zpd_zone
        task_data["estimated_minutes"] = min(task_data.get("estimated_minutes", 20), decision.max_minutes)

        challenge = ZPDChallenge(
            id=task_data["id"],
            user_id=user_id,
            role_id=role_id,
            title=task_data["title"],
            description=task_data["description"],
            task_type=task_data["task_type"],
            is_real_world=task_data["is_real_world"],
            difficulty=task_data["difficulty"],
            skill_domain=task_data["skill_domain"],
            estimated_minutes=task_data["estimated_minutes"],
            xp_reward=task_data["xp_reward"],
            status=ChallengeStatus.GENERATED.value,
            zpd_zone=task_data["zpd_zone"],
            scaffolding_hints=json.dumps(task_data["scaffolding_hints"], ensure_ascii=False),
            expires_at=task_data["expires_at"],
            created_at=task_data["created_at"],
        )

        self.db.add(challenge)
        self.db.commit()
        self.db.refresh(challenge)

        log_zpd_event(
            "challenge_drawn",
            user_id,
            role_id,
            challenge_id=challenge.id,
            details={"task_type": challenge.task_type, "difficulty": challenge.difficulty},
        )

        return self._to_dto(challenge)

    def get_active_challenge(self, user_id: str, role_id: str) -> Optional[ZPDChallengeDTO]:
        """
        Retrieve active challenge for role, performing lazy soft-expiration check if needed.
        """
        now = datetime.now(timezone.utc)
        challenge = (
            self.db.query(ZPDChallenge)
            .filter(
                ZPDChallenge.user_id == user_id,
                ZPDChallenge.role_id == role_id,
                ZPDChallenge.status == ChallengeStatus.ACCEPTED.value,
            )
            .first()
        )
        if not challenge:
            return None

        # Check soft expiration
        expires_at = challenge.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            logger.info("Challenge %s soft expired at %s", challenge.id, expires_at)
            challenge.status = ChallengeStatus.EXPIRED.value
            self.db.commit()
            log_zpd_event("challenge_expired", user_id, role_id, challenge_id=challenge.id)
            return None

        return self._to_dto(challenge)

    def accept_challenge(
        self,
        challenge_id: str,
        replace_existing: bool = True,
    ) -> ZPDChallengeDTO:
        """
        Accept generated challenge. If replace_existing=True, mark any currently active task as abandoned.
        """
        challenge = self.db.query(ZPDChallenge).filter(ZPDChallenge.id == challenge_id).first()
        if not challenge:
            raise ValueError(f"Challenge '{challenge_id}' not found")

        now = datetime.now(timezone.utc)

        # Check existing accepted challenge in this role slot
        if replace_existing:
            existing = (
                self.db.query(ZPDChallenge)
                .filter(
                    ZPDChallenge.user_id == challenge.user_id,
                    ZPDChallenge.role_id == challenge.role_id,
                    ZPDChallenge.status == ChallengeStatus.ACCEPTED.value,
                    ZPDChallenge.id != challenge.id,
                )
                .all()
            )
            for old in existing:
                old.status = ChallengeStatus.ABANDONED.value
                log_zpd_event("challenge_abandoned", old.user_id, old.role_id, challenge_id=old.id)

        challenge.status = ChallengeStatus.ACCEPTED.value
        challenge.accepted_at = now
        self.db.commit()
        self.db.refresh(challenge)

        log_zpd_event("challenge_accepted", challenge.user_id, challenge.role_id, challenge_id=challenge.id)
        return self._to_dto(challenge)

    def complete_challenge(
        self,
        challenge_id: str,
        user_feeling: str,
        user_action_plan: str,
        actual_minutes: Optional[int] = None,
    ) -> CompleteChallengeResponse:
        """
        Validate self-attestation reflection and settle XP via M6.5 ACID transaction.
        (Full implementation detailed in Phase 6 / US4)
        """
        if not user_feeling or not user_feeling.strip():
            raise ValueError("user_feeling is mandatory for self-attestation reflection")
        if not user_action_plan or not user_action_plan.strip():
            raise ValueError("user_action_plan is mandatory for self-attestation reflection")

        challenge = self.db.query(ZPDChallenge).filter(ZPDChallenge.id == challenge_id).first()
        if not challenge:
            raise ValueError(f"Challenge '{challenge_id}' not found")

        if challenge.status != ChallengeStatus.ACCEPTED.value:
            raise ValueError(f"Challenge must be in 'accepted' status to complete, but is '{challenge.status}'")

        now = datetime.now(timezone.utc)
        challenge.status = ChallengeStatus.COMPLETED.value
        challenge.completed_at = now

        # Update mastery in role_skill_mastery
        mastery = (
            self.db.query(RoleSkillMastery)
            .filter_by(
                user_id=challenge.user_id,
                role_id=challenge.role_id,
                skill_domain=challenge.skill_domain,
            )
            .first()
        )
        if not mastery:
            mastery = RoleSkillMastery(
                user_id=challenge.user_id,
                role_id=challenge.role_id,
                skill_domain=challenge.skill_domain,
                p_mastery=0.30,
                consecutive_successes=0,
                consecutive_failures=0,
            )
            self.db.add(mastery)

        # Bayesian Knowledge Tracing positive step
        mastery.consecutive_successes = (mastery.consecutive_successes or 0) + 1
        mastery.consecutive_failures = 0
        mastery.last_attempt_at = now

        from .bkt_tracker import BKTTracker
        tracker = BKTTracker()
        new_p = tracker.update_mastery(p_prev=mastery.p_mastery or 0.30, is_success=True)
        mastery.p_mastery = new_p

        # Atomic XP settlement into xp_ledger & users if present
        try:
            from sqlalchemy import text
            import uuid
            self.db.execute(
                text(
                    "UPDATE users SET current_xp = current_xp + :amount, lifetime_xp = lifetime_xp + :amount WHERE id = :user_id"
                ),
                {"amount": challenge.xp_reward, "user_id": challenge.user_id},
            )
            self.db.execute(
                text(
                    "INSERT INTO xp_ledger (id, user_id, role_id, amount, xp_type, reason, source_module, created_at) "
                    "VALUES (:id, :user_id, :role_id, :amount, 'earned', :reason, 'M4.11', :now)"
                ),
                {
                    "id": f"xp_tx_{uuid.uuid4().hex[:12]}",
                    "user_id": challenge.user_id,
                    "role_id": challenge.role_id,
                    "amount": challenge.xp_reward,
                    "reason": f"zpd_challenge_completed_{challenge.id}",
                    "now": now,
                },
            )
        except Exception as e:
            logger.debug("Ledger table or users table not present or direct update skipped: %s", e)

        self.db.commit()

        log_zpd_event(
            "challenge_completed",
            challenge.user_id,
            challenge.role_id,
            challenge_id=challenge.id,
            details={"awarded_xp": challenge.xp_reward, "new_p_mastery": new_p},
        )

        return CompleteChallengeResponse(
            success=True,
            awarded_xp=challenge.xp_reward,
            transaction_id=f"tx_{challenge.id}",
            new_p_mastery=new_p,
        )

    def _to_dto(self, challenge: ZPDChallenge) -> ZPDChallengeDTO:
        return ZPDChallengeDTO(
            id=challenge.id,
            role_id=challenge.role_id,
            title=challenge.title,
            description=challenge.description,
            task_type=TaskType(challenge.task_type),
            is_real_world=challenge.is_real_world,
            difficulty=TaskDifficulty(challenge.difficulty),
            skill_domain=challenge.skill_domain,
            estimated_minutes=challenge.estimated_minutes,
            xp_reward=challenge.xp_reward,
            status=ChallengeStatus(challenge.status),
            zpd_zone=challenge.zpd_zone,
            scaffolding_hints=challenge.get_hints(),
            accepted_at=challenge.accepted_at,
            expires_at=challenge.expires_at,
            created_at=challenge.created_at,
        )
