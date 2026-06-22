"""
M6.6 — Community PostgreSQL ORM Models (L3 Cloud)

SPEC: docs/modules/M3_7_community_ui_SPEC.md §7.3
Privacy: All 6 tables are L3 (cloud-only, no L1 raw data).
         social_posts.visibility defaults to 'private' (RISK-12).

Tables:
  - m6_6_communities       社群實體 (member_cap CHECK 2~8)
  - m6_6_community_members 成員關係 (admin/member 角色)
  - m6_6_social_posts      貼文 (預設 visibility='private')
  - m6_6_validations       同儕驗證 (unique: one vote per post per user)
  - m6_6_stakes            XP 質押紀錄 (held/won/forfeited)
  - m6_6_challenges        週期挑戰 (is_draft=true 預設)
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


from sqlalchemy import Table

class Base(DeclarativeBase):
    pass


# Stub users table to satisfy ForeignKey constraints in the community metadata registry
users_table = Table(
    "users",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("display_name", String(100), nullable=True),
)


class Community(Base):
    """社群實體 — member_cap 限制 2~8 人 (SPEC §10.1)"""
    __tablename__ = "m6_6_communities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    type = Column(
        String(20), nullable=False, default="user_created",
        comment="user_created | theme_random | system_random",
    )
    theme = Column(String(50), nullable=True, comment="主題標籤 (e.g. 'cooking', 'study')")
    member_cap = Column(Integer, nullable=False, default=5)
    goal = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    codex = Column(Text, nullable=True)
    rules = Column(Text, nullable=True, comment="JSON array of rule strings")
    quotes = Column(Text, nullable=True, comment="JSON array of quote strings")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=False, comment="User who created this community")

    # Relationships
    members = relationship("CommunityMember", back_populates="community", cascade="all, delete-orphan")
    posts = relationship("SocialPost", back_populates="community", cascade="all, delete-orphan")
    challenges = relationship("Challenge", back_populates="community", cascade="all, delete-orphan")
    join_requests = relationship("JoinRequest", back_populates="community", cascade="all, delete-orphan")

    challenge_mode = Column(
        String(20), nullable=False, default="manual",
        comment="manual | ai_reviewed | member_rotation",
    )

    __table_args__ = (
        CheckConstraint("member_cap >= 2 AND member_cap <= 8", name="chk_member_cap_range"),
    )


class CommunityMember(Base):
    """成員關係 — 角色: admin / member"""
    __tablename__ = "m6_6_community_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey("m6_6_communities.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(10), nullable=False, default="member", comment="admin | member")
    joined_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    community = relationship("Community", back_populates="members")

    __table_args__ = (
        UniqueConstraint("community_id", "user_id", name="uq_community_member"),
    )


class SocialPost(Base):
    """貼文 — 預設 visibility='private' (RISK-12)"""
    __tablename__ = "m6_6_social_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey("m6_6_communities.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    kind = Column(
        String(20), nullable=False, default="achievement",
        comment="achievement | encouragement | milestone",
    )
    visibility = Column(
        String(10), nullable=False, default="private",
        comment="private | community — RISK-12: defaults to private",
    )
    is_draft = Column(Boolean, nullable=False, default=True, comment="RISK-08: draft until user approves")
    likes_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    published_at = Column(DateTime(timezone=True), nullable=True)

    community = relationship("Community", back_populates="posts")
    validations = relationship("Validation", back_populates="post", cascade="all, delete-orphan")


class Validation(Base):
    """同儕驗證 — unique: 一人一貼文一次"""
    __tablename__ = "m6_6_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("m6_6_social_posts.id"), nullable=False)
    validator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    evidence_url = Column(String(512), nullable=True, comment="Optional proof link")
    validated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    post = relationship("SocialPost", back_populates="validations")

    __table_args__ = (
        UniqueConstraint("post_id", "validator_id", name="uq_validation_per_user"),
    )


class Stake(Base):
    """XP 質押紀錄 — status: held/won/forfeited"""
    __tablename__ = "m6_6_stakes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    community_id = Column(UUID(as_uuid=True), ForeignKey("m6_6_communities.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), nullable=True, comment="Optional: linked task")
    xp_amount = Column(Integer, nullable=False)
    status = Column(
        String(10), nullable=False, default="held",
        comment="held | won | forfeited",
    )
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    settled_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("xp_amount > 0", name="chk_stake_positive"),
    )


class Challenge(Base):
    """週期挑戰 — is_draft=true 預設 (RISK-18 L3 only context)"""
    __tablename__ = "m6_6_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey("m6_6_communities.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    period = Column(
        String(10), nullable=False, default="weekly",
        comment="weekly | monthly",
    )
    source = Column(
        String(20), nullable=False, default="admin",
        comment="admin | ai_generated | voted",
    )
    is_draft = Column(Boolean, nullable=False, default=True, comment="RISK-18: must approve before public")
    is_active = Column(Boolean, nullable=False, default=True)
    progress = Column(Integer, nullable=False, default=0, comment="Completion percentage 0-100")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    community = relationship("Community", back_populates="challenges")


class JoinRequest(Base):
    """社群加入申請"""
    __tablename__ = "m6_6_join_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id = Column(UUID(as_uuid=True), ForeignKey("m6_6_communities.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="pending", comment="pending | approved | rejected")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    community = relationship("Community", back_populates="join_requests")

    __table_args__ = (
        UniqueConstraint("community_id", "user_id", name="uq_community_user_request"),
    )
