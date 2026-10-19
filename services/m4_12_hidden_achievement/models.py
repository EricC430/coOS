import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class HiddenAchievementModel(Base):
    __tablename__ = "hidden_achievements"

    id = Column(String(64), primary_key=True)
    archetype = Column(String(32), nullable=False)  # curiosity, metacognition, restoration, cross_synthesis
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    flavor_text_template = Column(Text, nullable=False)
    rarity = Column(String(16), nullable=False)  # rare, epic, legendary
    exp_reward = Column(Integer, nullable=False)
    badge_icon_url = Column(String(255), nullable=False)
    eval_rules_json = Column(Text, nullable=False)
    is_hidden = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user_achievements = relationship("UserAchievementModel", back_populates="achievement")

    __table_args__ = (
        Index("idx_hidden_achievements_archetype", "archetype"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "archetype": self.archetype,
            "name": self.name,
            "description": self.description,
            "flavor_text_template": self.flavor_text_template,
            "rarity": self.rarity,
            "exp_reward": self.exp_reward,
            "badge_icon_url": self.badge_icon_url,
            "eval_rules_json": self.eval_rules_json,
            "is_hidden": self.is_hidden,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserAchievementModel(Base):
    __tablename__ = "user_achievements"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), nullable=False)
    achievement_id = Column(String(64), ForeignKey("hidden_achievements.id"), nullable=False)
    origin_role_id = Column(String(64), nullable=True)
    unlocked_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_acknowledged = Column(Boolean, nullable=False, default=False)
    xp_awarded = Column(Integer, nullable=False)
    transaction_id = Column(String(64), nullable=False)
    context_summary = Column(Text, nullable=True)

    achievement = relationship("HiddenAchievementModel", back_populates="user_achievements")

    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
        Index("idx_user_achievements_user", "user_id"),
        Index("idx_user_achievements_ack", "user_id", "is_acknowledged"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "achievement_id": self.achievement_id,
            "origin_role_id": self.origin_role_id,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
            "is_acknowledged": self.is_acknowledged,
            "xp_awarded": self.xp_awarded,
            "transaction_id": self.transaction_id,
            "context_summary": self.context_summary,
        }


class EpistemicEvidenceQueueModel(Base):
    __tablename__ = "epistemic_evidence_queue"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False)
    origin_role_id = Column(String(64), nullable=True)
    source_type = Column(String(32), nullable=False)  # chat_message, session_summary, daily_reflection
    raw_excerpt = Column(Text, nullable=False)
    extracted_themes_json = Column(Text, nullable=True)
    concept_leap_depth = Column(Float, nullable=False, default=0.0)
    proactivity_score = Column(Float, nullable=False, default=0.0)
    status = Column(String(16), nullable=False, default="PENDING")  # PENDING, PROCESSING, EVALUATED, FAILED
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_evidence_queue_status", "status"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "origin_role_id": self.origin_role_id,
            "source_type": self.source_type,
            "raw_excerpt": self.raw_excerpt,
            "extracted_themes_json": self.extracted_themes_json,
            "concept_leap_depth": self.concept_leap_depth,
            "proactivity_score": self.proactivity_score,
            "status": self.status,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }
