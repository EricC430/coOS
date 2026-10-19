import json
import uuid
from datetime import datetime, timezone
from typing import Any, List
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
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RoleSkillMastery(Base):
    __tablename__ = "role_skill_mastery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False)
    role_id = Column(String(64), nullable=False)
    skill_domain = Column(String(64), nullable=False)
    p_mastery = Column(Float, nullable=False, default=0.30)
    consecutive_successes = Column(Integer, nullable=False, default=0)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "skill_domain", name="uq_role_skill"),
        Index("idx_role_skill_lookup", "user_id", "role_id"),
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "skill_domain": self.skill_domain,
            "p_mastery": self.p_mastery,
            "consecutive_successes": self.consecutive_successes,
            "consecutive_failures": self.consecutive_failures,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ZPDChallenge(Base):
    __tablename__ = "zpd_challenges"

    id = Column(String(64), primary_key=True, default=lambda: f"zpd_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(64), nullable=False)
    role_id = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    task_type = Column(String(32), nullable=False, default="skill_stretch")
    is_real_world = Column(Boolean, nullable=False, default=False)
    difficulty = Column(String(32), nullable=False)
    skill_domain = Column(String(64), nullable=False)
    estimated_minutes = Column(Integer, nullable=False, default=20)
    xp_reward = Column(Integer, nullable=False, default=50)
    status = Column(String(32), nullable=False, default="generated")
    zpd_zone = Column(String(32), nullable=False)
    scaffolding_hints = Column(Text, nullable=False, default="[]")
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_zpd_active_slot", "user_id", "role_id", "status"),
    )

    def get_hints(self) -> List[str]:
        if not self.scaffolding_hints:
            return []
        try:
            val = json.loads(self.scaffolding_hints)
            return val if isinstance(val, list) else []
        except Exception:
            return []

    def set_hints(self, hints: List[str]) -> None:
        self.scaffolding_hints = json.dumps(hints, ensure_ascii=False)
