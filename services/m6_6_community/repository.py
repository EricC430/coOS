"""
M6.6 — Community Repository (CRUD + Isolation Guards)

SPEC: docs/modules/M3_7_community_ui_SPEC.md §7.3–§7.4
All queries enforce community_id + member-check isolation (M4.13.3).
"""
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    Challenge,
    Community,
    CommunityMember,
    SocialPost,
    Stake,
    Validation,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Member-check helper (M4.13.3 isolation)
# ---------------------------------------------------------------------------

def _assert_member(session: Session, community_id: uuid.UUID, user_id: uuid.UUID) -> CommunityMember:
    """Raise if user is not an active member of the community."""
    member = session.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user_id,
            CommunityMember.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()
    if member is None:
        raise PermissionError(f"User {user_id} is not a member of community {community_id}")
    return member


# ---------------------------------------------------------------------------
# Community CRUD
# ---------------------------------------------------------------------------

def list_user_communities(session: Session, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """List communities the user has joined."""
    rows = session.execute(
        select(Community, CommunityMember)
        .join(CommunityMember, Community.id == CommunityMember.community_id)
        .where(
            CommunityMember.user_id == user_id,
            CommunityMember.is_active == True,  # noqa: E712
            Community.is_active == True,  # noqa: E712
        )
        .order_by(CommunityMember.joined_at)
    ).all()

    results = []
    for community, membership in rows:
        member_count = session.execute(
            select(func.count(CommunityMember.id)).where(
                CommunityMember.community_id == community.id,
                CommunityMember.is_active == True,  # noqa: E712
            )
        ).scalar() or 0

        results.append({
            "id": str(community.id),
            "name": community.name,
            "type": community.type,
            "theme": community.theme,
            "member_cap": community.member_cap,
            "member_count": member_count,
            "is_member": True,
            "role": membership.role,
            "challenge_mode": community.challenge_mode or "manual",
            "goal": community.goal,
            "vision": community.vision,
            "codex": community.codex,
            "rules": json.loads(community.rules) if community.rules else [],
            "quotes": json.loads(community.quotes) if community.quotes else [],
        })
    return results


def create_community(
    session: Session,
    user_id: uuid.UUID,
    name: str,
    community_type: str = "user_created",
    theme: str | None = None,
    member_cap: int = 5,
) -> dict[str, Any]:
    """Create a new community and add creator as admin."""
    community = Community(
        name=name,
        type=community_type,
        theme=theme,
        member_cap=member_cap,
        created_by=user_id,
    )
    session.add(community)
    session.flush()  # Get the generated ID

    member = CommunityMember(
        community_id=community.id,
        user_id=user_id,
        role="admin",
    )
    session.add(member)
    session.flush()

    return {
        "id": str(community.id),
        "name": community.name,
        "type": community.type,
        "member_cap": community.member_cap,
        "member_count": 1,
    }


def join_community(
    session: Session,
    user_id: uuid.UUID,
    mode: str = "system_random",
    theme: str | None = None,
) -> dict[str, Any]:
    """
    Join a community by mode:
      - theme_random: join a random community with matching theme that has space
      - system_random: join any random community that has space
    """
    query = (
        select(Community)
        .where(Community.is_active == True)  # noqa: E712
    )

    if mode == "theme_random" and theme:
        query = query.where(Community.theme == theme)

    communities = session.execute(query).scalars().all()

    for community in communities:
        member_count = session.execute(
            select(func.count(CommunityMember.id)).where(
                CommunityMember.community_id == community.id,
                CommunityMember.is_active == True,  # noqa: E712
            )
        ).scalar() or 0

        # Check if user is already a member
        existing = session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == user_id,
            )
        ).scalar_one_or_none()

        if existing is None and member_count < community.member_cap:
            member = CommunityMember(
                community_id=community.id,
                user_id=user_id,
                role="member",
            )
            session.add(member)
            session.flush()
            return {
                "id": str(community.id),
                "name": community.name,
                "type": community.type,
                "member_count": member_count + 1,
                "joined": True,
            }

    raise ValueError("No available community found for the given criteria")


# ---------------------------------------------------------------------------
# Codex
# ---------------------------------------------------------------------------

def get_community_codex(session: Session, community_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    """Get the community codex (goal/vision/codex/quotes/rules). Requires membership."""
    _assert_member(session, community_id, user_id)
    community = session.get(Community, community_id)
    if community is None:
        raise ValueError("Community not found")
    return {
        "goal": community.goal or "",
        "vision": community.vision or "",
        "codex": community.codex or "",
        "quotes": json.loads(community.quotes) if community.quotes else [],
        "rules": json.loads(community.rules) if community.rules else [],
    }


def update_community_codex(
    session: Session,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    goal: str,
    vision: str,
    codex: str,
    rules: list[str],
    quotes: list[str],
) -> dict[str, Any]:
    """Update the community codex. Requires membership."""
    _assert_member(session, community_id, user_id)
    community = session.get(Community, community_id)
    if community is None:
        raise ValueError("Community not found")
    community.goal = goal
    community.vision = vision
    community.codex = codex
    community.rules = json.dumps(rules)
    community.quotes = json.dumps(quotes)
    session.flush()
    return {
        "goal": community.goal or "",
        "vision": community.vision or "",
        "codex": community.codex or "",
        "quotes": quotes,
        "rules": rules,
    }


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

def get_community_posts(
    session: Session,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """Get published posts in a community. Requires membership (isolation)."""
    _assert_member(session, community_id, user_id)

    posts = session.execute(
        select(SocialPost)
        .where(
            SocialPost.community_id == community_id,
            SocialPost.is_draft == False,  # noqa: E712
            SocialPost.visibility == "community",
        )
        .order_by(SocialPost.published_at.desc())
        .limit(limit)
    ).scalars().all()

    return [
        {
            "id": str(p.id),
            "author_id": str(p.author_id),
            "content": p.content,
            "kind": p.kind,
            "likes_count": p.likes_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "validation_count": len(p.validations) if p.validations else 0,
        }
        for p in posts
    ]


def create_post_draft(
    session: Session,
    user_id: uuid.UUID,
    community_id: uuid.UUID,
    content: str,
    kind: str = "achievement",
) -> dict[str, Any]:
    """Create a draft post. Returns with privacy_warning per RISK-12."""
    _assert_member(session, community_id, user_id)

    post = SocialPost(
        community_id=community_id,
        author_id=user_id,
        content=content,
        kind=kind,
        is_draft=True,
        visibility="private",
    )
    session.add(post)
    session.flush()

    return {
        "id": str(post.id),
        "is_draft": True,
        "privacy_warning": "此貼文將對社群成員可見。請確認不含敏感個人資訊。",
    }


def publish_post(session: Session, draft_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    """Approve and publish a draft post."""
    post = session.get(SocialPost, draft_id)
    if post is None:
        raise ValueError("Post not found")
    if str(post.author_id) != str(user_id):
        raise PermissionError("Only the author can publish this post")
    if not post.is_draft:
        raise ValueError("Post is already published")

    post.is_draft = False
    post.visibility = "community"
    post.published_at = datetime.now(UTC)
    session.flush()

    return {
        "id": str(post.id),
        "published": True,
        "published_at": post.published_at.isoformat(),
    }


def like_post(session: Session, post_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    """Like a published post. Requires membership in the same community."""
    post = session.get(SocialPost, post_id)
    if post is None:
        raise ValueError("Post not found")
    _assert_member(session, post.community_id, user_id)

    post.likes_count = (post.likes_count or 0) + 1
    session.flush()
    return {"id": str(post.id), "likes_count": post.likes_count}


# ---------------------------------------------------------------------------
# Validations
# ---------------------------------------------------------------------------

def create_validation(
    session: Session,
    post_id: uuid.UUID,
    validator_id: uuid.UUID,
    evidence_url: str | None = None,
) -> dict[str, Any]:
    """Create a peer validation for a post (unique per user per post)."""
    post = session.get(SocialPost, post_id)
    if post is None:
        raise ValueError("Post not found")
    _assert_member(session, post.community_id, validator_id)

    # Check duplicate
    existing = session.execute(
        select(Validation).where(
            Validation.post_id == post_id,
            Validation.validator_id == validator_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("You have already validated this post")

    validation = Validation(
        post_id=post_id,
        validator_id=validator_id,
        evidence_url=evidence_url,
    )
    session.add(validation)
    session.flush()

    return {
        "id": str(validation.id),
        "post_id": str(post_id),
        "validated_at": validation.validated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Stakes
# ---------------------------------------------------------------------------

def list_user_stakes(session: Session, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """List all stakes for a user."""
    stakes = session.execute(
        select(Stake)
        .where(Stake.user_id == user_id)
        .order_by(Stake.created_at.desc())
    ).scalars().all()

    return [
        {
            "id": str(s.id),
            "community_id": str(s.community_id),
            "task_id": str(s.task_id) if s.task_id else None,
            "xp_amount": s.xp_amount,
            "status": s.status,
            "deadline": s.deadline.isoformat() if s.deadline else None,
            "created_at": s.created_at.isoformat(),
        }
        for s in stakes
    ]


def create_stake(
    session: Session,
    user_id: uuid.UUID,
    community_id: uuid.UUID,
    xp_amount: int,
    task_id: uuid.UUID | None = None,
    deadline: datetime | None = None,
) -> dict[str, Any]:
    """Create a stake record (XP hold is done via M6.5 gatekeeper)."""
    _assert_member(session, community_id, user_id)

    stake = Stake(
        user_id=user_id,
        community_id=community_id,
        task_id=task_id,
        xp_amount=xp_amount,
        deadline=deadline,
        status="held",
    )
    session.add(stake)
    session.flush()

    return {
        "id": str(stake.id),
        "community_id": str(stake.community_id),
        "task_id": str(stake.task_id) if stake.task_id else None,
        "xp_amount": stake.xp_amount,
        "status": stake.status,
        "deadline": stake.deadline.isoformat() if stake.deadline else None,
        "created_at": stake.created_at.isoformat() if stake.created_at else datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Challenges
# ---------------------------------------------------------------------------

def get_community_challenges(
    session: Session,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Get challenges for a community (only non-draft for regular members, both for admin)."""
    member = _assert_member(session, community_id, user_id)
    is_admin = member.role == "admin"

    stmt = select(Challenge).where(
        Challenge.community_id == community_id,
        Challenge.is_active == True,  # noqa: E712
    )
    if not is_admin:
        stmt = stmt.where(Challenge.is_draft == False)  # noqa: E712

    challenges = session.execute(
        stmt.order_by(Challenge.created_at.desc())
    ).scalars().all()

    return [
        {
            "id": str(c.id),
            "title": c.title,
            "description": c.description,
            "period": c.period,
            "source": c.source,
            "progress": c.progress,
            "is_draft": c.is_draft,
            "created_at": c.created_at.isoformat(),
        }
        for c in challenges
    ]


def create_challenge(
    session: Session,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    description: str | None = None,
    period: str = "weekly",
    source: str = "admin",
    is_draft: bool = False,
) -> dict[str, Any]:
    """Create a challenge for the community."""
    _assert_member(session, community_id, user_id)
    challenge = Challenge(
        community_id=community_id,
        title=title,
        description=description,
        period=period,
        source=source,
        is_draft=is_draft,
        is_active=True,
        progress=0,
    )
    session.add(challenge)
    session.flush()
    return {
        "id": str(challenge.id),
        "title": challenge.title,
        "description": challenge.description,
        "period": challenge.period,
        "source": challenge.source,
        "progress": challenge.progress,
        "is_draft": challenge.is_draft,
        "created_at": challenge.created_at.isoformat(),
    }


def approve_challenge(
    session: Session,
    challenge_id: uuid.UUID,
    user_id: uuid.UUID,
    edits: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Admin approves a draft challenge (publishes it)."""
    challenge = session.get(Challenge, challenge_id)
    if challenge is None:
        raise ValueError("Challenge not found")

    # Check admin role
    member = _assert_member(session, challenge.community_id, user_id)
    if member.role != "admin":
        raise PermissionError("Only admins can approve challenges")

    if edits:
        if "title" in edits:
            challenge.title = edits["title"]
        if "description" in edits:
            challenge.description = edits["description"]

    challenge.is_draft = False
    session.flush()

    return {"id": str(challenge.id), "approved": True}


# ---------------------------------------------------------------------------
# Commitments (tasks → commitments → validation closed loop)
# ---------------------------------------------------------------------------

def get_community_commitments(
    session: Session,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Get the closed-loop view: tasks to claim + active commitments + validations.
    Returns three lists for the CommitmentClosedLoop UI.
    """
    _assert_member(session, community_id, user_id)

    # Unclaimed tasks: posts in draft state by other users (simplified model)
    # In full implementation, tasks would be a separate entity
    # For now, we model "tasks" as community challenges that are active

    # Active commitments: user's posts (achievements/milestones only) that are published but not yet validated
    user_posts = session.execute(
        select(SocialPost)
        .where(
            SocialPost.community_id == community_id,
            SocialPost.author_id == user_id,
            SocialPost.is_draft == False,  # noqa: E712
            SocialPost.kind.in_(["achievement", "milestone"]),
        )
        .order_by(SocialPost.published_at.desc())
    ).scalars().all()

    commitments = []
    for p in user_posts:
        val_count = session.execute(
            select(func.count(Validation.id)).where(Validation.post_id == p.id)
        ).scalar() or 0
        commitments.append({
            "id": str(p.id),
            "content": p.content,
            "kind": p.kind,
            "validation_count": val_count,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        })

    # Posts needing validation (achievements/milestones only, from other users in community)
    to_validate = session.execute(
        select(SocialPost)
        .where(
            SocialPost.community_id == community_id,
            SocialPost.is_draft == False,  # noqa: E712
            SocialPost.author_id != user_id,
            SocialPost.kind.in_(["achievement", "milestone"]),
        )
        .order_by(SocialPost.published_at.desc())
        .limit(10)
    ).scalars().all()

    tasks_to_validate = [
        {
            "id": str(p.id),
            "content": p.content,
            "kind": p.kind,
            "author_id": str(p.author_id),
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in to_validate
    ]

    # User's stakes
    stakes = session.execute(
        select(Stake)
        .where(
            Stake.community_id == community_id,
            Stake.user_id == user_id,
            Stake.status == "held",
        )
    ).scalars().all()

    active_stakes = [
        {
            "id": str(s.id),
            "xp_amount": s.xp_amount,
            "deadline": s.deadline.isoformat() if s.deadline else None,
        }
        for s in stakes
    ]

    return {
        "commitments": commitments,
        "to_validate": tasks_to_validate,
        "active_stakes": active_stakes,
    }


# ---------------------------------------------------------------------------
# Community Administration & Role Management
# ---------------------------------------------------------------------------

def get_community_members(session: Session, community_id: uuid.UUID, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Get all active members of a community. Requires membership."""
    _assert_member(session, community_id, user_id)
    
    from .models import users_table
    stmt = (
        select(
            CommunityMember.user_id,
            CommunityMember.role,
            CommunityMember.joined_at,
            users_table.c.display_name
        )
        .select_from(CommunityMember)
        .outerjoin(users_table, CommunityMember.user_id == users_table.c.id)
        .where(
            CommunityMember.community_id == community_id,
            CommunityMember.is_active == True
        )
        .order_by(CommunityMember.joined_at)
    )
    
    rows = session.execute(stmt).all()
    return [
        {
            "user_id": str(r.user_id),
            "role": r.role,
            "joined_at": r.joined_at.isoformat(),
            "display_name": r.display_name or f"User-{str(r.user_id)[:4]}"
        }
        for r in rows
    ]


def update_member_role(
    session: Session,
    community_id: uuid.UUID,
    requesting_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role: str
) -> dict[str, Any]:
    """Promote or demote a member. Requires admin role."""
    req_member = _assert_member(session, community_id, requesting_user_id)
    if req_member.role != "admin":
        raise PermissionError("Only admins can manage member roles")
        
    target_member = _assert_member(session, community_id, target_user_id)
    
    # Last admin demotion guard
    if target_member.role == "admin" and role == "member":
        admin_count = session.execute(
            select(func.count(CommunityMember.id)).where(
                CommunityMember.community_id == community_id,
                CommunityMember.role == "admin",
                CommunityMember.is_active == True
            )
        ).scalar() or 0
        if admin_count <= 1:
            raise ValueError("無法取消管理員權限，因為該成員是此社群的唯一管理員")
            
    target_member.role = role
    session.flush()
    return {"user_id": str(target_user_id), "role": role}


def kick_member(
    session: Session,
    community_id: uuid.UUID,
    requesting_user_id: uuid.UUID,
    target_user_id: uuid.UUID
) -> dict[str, Any]:
    """Kick a member. Requires admin role."""
    req_member = _assert_member(session, community_id, requesting_user_id)
    if req_member.role != "admin":
        raise PermissionError("Only admins can kick members")
        
    if requesting_user_id == target_user_id:
        raise ValueError("您不能踢除您自己，請使用退出社群功能")
        
    target_member = _assert_member(session, community_id, target_user_id)
    
    # Last admin kick guard
    if target_member.role == "admin":
        admin_count = session.execute(
            select(func.count(CommunityMember.id)).where(
                CommunityMember.community_id == community_id,
                CommunityMember.role == "admin",
                CommunityMember.is_active == True
            )
        ).scalar() or 0
        if admin_count <= 1:
            raise ValueError("無法踢除管理員，因為該成員是此社群的唯一管理員")
            
    target_member.is_active = False
    session.flush()
    return {"user_id": str(target_user_id), "kicked": True}


def leave_community(session: Session, community_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    """Leave the community."""
    member = _assert_member(session, community_id, user_id)
    
    # Get active members count
    active_count = session.execute(
        select(func.count(CommunityMember.id)).where(
            CommunityMember.community_id == community_id,
            CommunityMember.is_active == True
        )
    ).scalar() or 0
    
    if member.role == "admin" and active_count > 1:
        # Check if there's another admin
        admin_count = session.execute(
            select(func.count(CommunityMember.id)).where(
                CommunityMember.community_id == community_id,
                CommunityMember.role == "admin",
                CommunityMember.is_active == True
            )
        ).scalar() or 0
        if admin_count <= 1:
            raise ValueError("無法退出社群，因為您是此社群唯一的管理員。請先指派其他成員為管理員")
            
    member.is_active = False
    session.flush()
    
    # If no members left, deactivate the community
    if active_count <= 1:
        community = session.get(Community, community_id)
        if community:
            community.is_active = False
            session.flush()
            
    return {"community_id": str(community_id), "left": True}


def get_join_requests(session: Session, community_id: uuid.UUID, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """Get pending join requests. Requires admin role."""
    member = _assert_member(session, community_id, user_id)
    if member.role != "admin":
        raise PermissionError("Only admins can view join requests")
        
    from .models import JoinRequest, users_table
    rows = session.execute(
        select(JoinRequest, users_table.c.display_name)
        .select_from(JoinRequest)
        .outerjoin(users_table, JoinRequest.user_id == users_table.c.id)
        .where(
            JoinRequest.community_id == community_id,
            JoinRequest.status == "pending"
        )
        .order_by(JoinRequest.created_at.desc())
    ).all()
    
    return [
        {
            "id": str(r.JoinRequest.id),
            "community_id": str(r.JoinRequest.community_id),
            "user_id": str(r.JoinRequest.user_id),
            "status": r.JoinRequest.status,
            "created_at": r.JoinRequest.created_at.isoformat(),
            "display_name": r.display_name or f"User-{str(r.JoinRequest.user_id)[:4]}"
        }
        for r in rows
    ]


def create_join_request(session: Session, community_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    """Create a pending join request."""
    # Check if already a member
    existing = session.execute(
        select(CommunityMember).where(
            CommunityMember.community_id == community_id,
            CommunityMember.user_id == user_id,
            CommunityMember.is_active == True
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("您已是該社群成員")
        
    # Check if pending request exists
    from .models import JoinRequest
    existing_req = session.execute(
        select(JoinRequest).where(
            JoinRequest.community_id == community_id,
            JoinRequest.user_id == user_id,
            JoinRequest.status == "pending"
        )
    ).scalar_one_or_none()
    if existing_req:
        raise ValueError("已送出加入申請，請等待管理員審核")
        
    req = JoinRequest(
        community_id=community_id,
        user_id=user_id,
        status="pending"
    )
    session.add(req)
    session.flush()
    return {
        "id": str(req.id),
        "community_id": str(community_id),
        "status": req.status
    }


def handle_join_request(
    session: Session,
    community_id: uuid.UUID,
    requesting_user_id: uuid.UUID,
    request_id: uuid.UUID,
    action: str
) -> dict[str, Any]:
    """Approve or reject a join request. Requires admin role."""
    member = _assert_member(session, community_id, requesting_user_id)
    if member.role != "admin":
        raise PermissionError("Only admins can approve/reject join requests")
        
    from .models import JoinRequest
    req = session.get(JoinRequest, request_id)
    if req is None or req.community_id != community_id:
        raise ValueError("Join request not found")
        
    if req.status != "pending":
        raise ValueError("該申請已被處理")
        
    if action == "approve":
        # Check community capacity
        community = session.get(Community, community_id)
        if community is None:
            raise ValueError("Community not found")
            
        member_count = session.execute(
            select(func.count(CommunityMember.id)).where(
                CommunityMember.community_id == community_id,
                CommunityMember.is_active == True
            )
        ).scalar() or 0
        
        if member_count >= community.member_cap:
            raise ValueError(f"無法加入，該社群已達人數上限 {community.member_cap} 人 (鄧巴數限制)")
            
        # Add community member
        new_member = CommunityMember(
            community_id=community_id,
            user_id=req.user_id,
            role="member"
        )
        session.add(new_member)
        req.status = "approved"
    elif action == "reject":
        req.status = "rejected"
    else:
        raise ValueError("Invalid action")
        
    session.flush()
    return {"request_id": str(request_id), "status": req.status}


def update_community_settings(
    session: Session,
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    challenge_mode: str,
    member_cap: int
) -> dict[str, Any]:
    """Update community settings. Requires admin role."""
    member = _assert_member(session, community_id, user_id)
    if member.role != "admin":
        raise PermissionError("Only admins can update community settings")
        
    community = session.get(Community, community_id)
    if community is None:
        raise ValueError("Community not found")
        
    if member_cap < 2 or member_cap > 8:
        raise ValueError("人數上限必須在 2 至 8 人之間 (鄧巴數限制)")
        
    # Check current active members count
    member_count = session.execute(
        select(func.count(CommunityMember.id)).where(
            CommunityMember.community_id == community_id,
            CommunityMember.is_active == True
        )
    ).scalar() or 0
    
    if member_cap < member_count:
        raise ValueError(f"人數上限不能少於當前成員數 ({member_count} 人)")
        
    community.challenge_mode = challenge_mode
    community.member_cap = member_cap
    session.flush()
    
    return {
        "id": str(community_id),
        "challenge_mode": challenge_mode,
        "member_cap": member_cap
    }


def list_explore_communities(session: Session, user_id: uuid.UUID) -> list[dict[str, Any]]:
    """List communities that the user is not currently in."""
    # Find community IDs user is active in
    joined_ids = session.execute(
        select(CommunityMember.community_id).where(
            CommunityMember.user_id == user_id,
            CommunityMember.is_active == True
        )
    ).scalars().all()
    
    # Query active communities user has not joined
    query = select(Community).where(Community.is_active == True)
    if joined_ids:
        query = query.where(~Community.id.in_(joined_ids))
        
    communities = session.execute(query).scalars().all()
    
    results = []
    from .models import JoinRequest
    for c in communities:
        member_count = session.execute(
            select(func.count(CommunityMember.id)).where(
                CommunityMember.community_id == c.id,
                CommunityMember.is_active == True
            )
        ).scalar() or 0
        
        # Check if user has a pending request for this community
        pending_req = session.execute(
            select(JoinRequest).where(
                JoinRequest.community_id == c.id,
                JoinRequest.user_id == user_id,
                JoinRequest.status == "pending"
            )
        ).scalar_one_or_none()
        
        results.append({
            "id": str(c.id),
            "name": c.name,
            "type": c.type,
            "theme": c.theme,
            "member_cap": c.member_cap,
            "member_count": member_count,
            "is_member": False,
            "role": "none",
            "is_pending": pending_req is not None,
            "challenge_mode": c.challenge_mode or "manual",
            "goal": "申請審核中..." if pending_req is not None else (c.goal or ""),
            "vision": c.vision or "",
            "codex": c.codex or "",
            "rules": json.loads(c.rules) if c.rules else [],
            "quotes": json.loads(c.quotes) if c.quotes else [],
        })
    return results

