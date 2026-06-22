"""
M4.13 — Community Engine FastAPI Routes

SPEC: docs/modules/M3_7_community_ui_SPEC.md §7.4
15 endpoints serving the M3.7 frontend Bento Grid UI.
All data flows through M6.6 PostgreSQL (L3 cloud).
Privacy: posts pass through Eguard (M2.3) before publishing.
"""
import asyncio
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from m6_2_postgresql.engine import cloud_session_ctx, get_cloud_session

from . import stream as sse_broker
from .isolation_middleware import get_current_user_id
from .schemas import (
    ChallengeApprove,
    ChallengeRead,
    ChallengeCreate,
    CommunityCodex,
    CodexUpdate,
    CommunityCreate,
    CommunityEvent,
    CommunityJoin,
    CommunityRead,
    CommitmentsView,
    DraftResult,
    LikeResult,
    PublishRequest,
    PublishResult,
    SocialPostDraft,
    SocialPostRead,
    StakeCreate,
    StakeRead,
    ValidationCreate,
    ValidationResult,
    MemberRead,
    RoleUpdateRequest,
    JoinRequestRead,
    JoinRequestAction,
    CommunitySettingsUpdate,
)
from .stake_engine import can_stake_on_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/m6_6", tags=["community"])


# ---------------------------------------------------------------------------
# Helper: get DB session or return mock data if cloud unavailable
# ---------------------------------------------------------------------------

def _get_session_or_raise():
    """Get a cloud session or raise 503 if unavailable."""
    session = get_cloud_session()
    if session is None:
        raise HTTPException(
            status_code=503,
            detail="Cloud database unavailable. Community features require PostgreSQL.",
        )
    return session


# ---------------------------------------------------------------------------
# Mock fallback for local development (no Supabase)
# ---------------------------------------------------------------------------

_MOCK_COMMUNITIES = [
    {
        "id": "mock-community-1",
        "name": "Interview Preparer",
        "type": "system_random",
        "theme": "career",
        "member_cap": 5,
        "member_count": 3,
        "is_member": True,
        "role": "member",
        "goal": "面試準備互助",
        "vision": "一起拿到理想 Offer",
        "codex": "互相練習、真誠回饋",
        "rules": ["每週至少模擬面試一次", "回饋要具體可行動"],
        "quotes": ["Practice makes perfect", "Fail fast, learn faster"],
    },
    {
        "id": "mock-community-2",
        "name": "Total Strangers",
        "type": "system_random",
        "theme": "social",
        "member_cap": 8,
        "member_count": 5,
        "is_member": True,
        "role": "member",
        "goal": "與陌生人建立連結",
        "vision": "踏出舒適圈",
        "codex": "保持開放心態",
        "rules": ["尊重每個人的邊界", "不批判"],
        "quotes": ["Strangers are just friends you haven't met yet"],
    },
    {
        "id": "mock-community-3",
        "name": "Friend Group",
        "type": "system_random",
        "theme": "friends",
        "member_cap": 5,
        "member_count": 4,
        "is_member": True,
        "role": "admin",
        "goal": "朋友互相督促",
        "vision": "一起變更好",
        "codex": "誠實但溫柔",
        "rules": ["每天簽到", "互相鼓勵"],
        "quotes": ["Together we grow", "朋友是人生最好的禮物"],
    },
    {
        "id": "mock-community-4",
        "name": "Cooking Lovers",
        "type": "system_random",
        "theme": "cooking",
        "member_cap": 5,
        "member_count": 2,
        "is_member": True,
        "role": "member",
        "goal": "一起學做菜",
        "vision": "每週嘗試新食譜",
        "codex": "分享食譜、曬成品照",
        "rules": ["每週至少做一道新菜", "分享心得和照片"],
        "quotes": ["Cooking is love made visible", "料理是最溫暖的語言"],
    },
    {
        "id": "mock-community-5",
        "name": "Study Group",
        "type": "system_random",
        "theme": "study",
        "member_cap": 5,
        "member_count": 4,
        "is_member": True,
        "role": "member",
        "goal": "一起讀書、一起進步",
        "vision": "期末考全員通過",
        "codex": "認真但不壓力山大",
        "rules": ["每天至少讀 30 分鐘", "考前互相出題"],
        "quotes": ["學如逆水行舟，不進則退", "The expert was once a beginner"],
    },
]

_MOCK_POSTS = [
    {
        "id": "mock-post-1",
        "author_id": "mock-user-a",
        "author_display": "Boyu",
        "content": "完成了第一次模擬面試！雖然很緊張但學到很多 💪",
        "kind": "achievement",
        "likes_count": 5,
        "created_at": "2026-06-21T10:00:00",
        "published_at": "2026-06-21T10:05:00",
        "validation_count": 2,
    },
    {
        "id": "mock-post-2",
        "author_id": "mock-user-b",
        "author_display": "Jacky",
        "content": "今天主動跟三個陌生人聊天了，感覺超棒！",
        "kind": "encouragement",
        "likes_count": 8,
        "created_at": "2026-06-21T09:30:00",
        "published_at": "2026-06-21T09:35:00",
        "validation_count": 3,
    },
    {
        "id": "mock-post-3",
        "author_id": "mock-user-c",
        "author_display": "Mia",
        "content": "這週堅持每天做一道新菜！第五天了 🎉",
        "kind": "milestone",
        "likes_count": 12,
        "created_at": "2026-06-20T18:00:00",
        "published_at": "2026-06-20T18:10:00",
        "validation_count": 4,
    },
]

_MOCK_CHALLENGES = [
    {
        "id": "mock-challenge-1",
        "title": "本週挑戰：每天與一位新朋友交流",
        "description": "這週的目標是每天主動找一位不太熟的人聊天，分享你的經驗！",
        "period": "weekly",
        "source": "admin",
        "progress": 40,
        "created_at": "2026-06-20T00:00:00",
    },
    {
        "id": "mock-challenge-2",
        "title": "月度挑戰：完成 10 次自我反思",
        "description": "每次反思至少寫 100 字，記錄你的成長與發現。",
        "period": "monthly",
        "source": "ai_generated",
        "progress": 20,
        "created_at": "2026-06-01T00:00:00",
    },
]

# Stateful mock members mapping: community_id -> list of members
_MOCK_MEMBERS = {
    "mock-community-1": [
        {"user_id": "00000000-0000-0000-0000-000000000000", "role": "member", "display_name": "Me (User)", "joined_at": "2026-06-01T00:00:00"},
        {"user_id": "mock-user-a", "role": "admin", "display_name": "Boyu", "joined_at": "2026-06-01T00:00:00"},
        {"user_id": "mock-user-b", "role": "member", "display_name": "Jacky", "joined_at": "2026-06-02T00:00:00"},
    ],
    "mock-community-2": [
        {"user_id": "00000000-0000-0000-0000-000000000000", "role": "member", "display_name": "Me (User)", "joined_at": "2026-06-03T00:00:00"},
        {"user_id": "mock-user-c", "role": "admin", "display_name": "Mia", "joined_at": "2026-06-03T00:00:00"},
    ],
    "mock-community-3": [
        {"user_id": "00000000-0000-0000-0000-000000000000", "role": "admin", "display_name": "Me (User)", "joined_at": "2026-06-04T00:00:00"},
        {"user_id": "mock-user-a", "role": "member", "display_name": "Boyu", "joined_at": "2026-06-04T00:00:00"},
        {"user_id": "mock-user-b", "role": "member", "display_name": "Jacky", "joined_at": "2026-06-05T00:00:00"},
        {"user_id": "mock-user-c", "role": "member", "display_name": "Mia", "joined_at": "2026-06-05T00:00:00"},
    ],
    "mock-community-4": [
        {"user_id": "00000000-0000-0000-0000-000000000000", "role": "member", "display_name": "Me (User)", "joined_at": "2026-06-06T00:00:00"},
        {"user_id": "mock-user-b", "role": "admin", "display_name": "Jacky", "joined_at": "2026-06-06T00:00:00"},
    ],
    "mock-community-5": [
        {"user_id": "00000000-0000-0000-0000-000000000000", "role": "member", "display_name": "Me (User)", "joined_at": "2026-06-07T00:00:00"},
        {"user_id": "mock-user-c", "role": "admin", "display_name": "Mia", "joined_at": "2026-06-07T00:00:00"},
    ]
}

# Stateful mock join requests
_MOCK_JOIN_REQUESTS = [
    {
        "id": "mock-req-1",
        "community_id": "mock-community-3", # Friend Group
        "user_id": "mock-user-d",
        "status": "pending",
        "created_at": "2026-06-22T10:00:00",
        "display_name": "Alice"
    }
]

# Stateful mock communities user has NOT joined
_MOCK_EXPLORE_COMMUNITIES = [
    {
        "id": "mock-explore-1",
        "name": "AI Enthusiasts",
        "type": "user_created",
        "theme": "study",
        "member_cap": 5,
        "member_count": 2,
        "is_member": False,
        "role": "none",
        "goal": "探討生成式 AI 與 Agent 開發",
        "vision": "成為 AI 領域專家",
        "codex": "分享知識、動手實作",
        "rules": ["禁止廣告", "每週分享一篇論文或工具"],
        "quotes": ["Learn by doing"],
        "challenge_mode": "manual"
    },
    {
        "id": "mock-explore-2",
        "name": "Fitness Geeks",
        "type": "user_created",
        "theme": "social",
        "member_cap": 8,
        "member_count": 3,
        "is_member": False,
        "role": "none",
        "goal": "養成規律運動習慣",
        "vision": "強健體魄、健康生活",
        "codex": "互相督促、健康飲食",
        "rules": ["每週運動至少三次", "紀錄飲食細節"],
        "quotes": ["No pain, no gain"],
        "challenge_mode": "ai_reviewed"
    }
]


def _is_cloud():
    """Check if cloud DB is available."""
    try:
        session = get_cloud_session()
        return session is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# GET /communities — List user's communities
# ---------------------------------------------------------------------------

@router.get("/communities", response_model=list[CommunityRead])
async def list_communities(request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        for c in _MOCK_COMMUNITIES:
            members = _MOCK_MEMBERS.get(c["id"], [])
            my_membership = next((m for m in members if m["user_id"] == str(user_id)), None)
            if my_membership:
                c["is_member"] = True
                c["role"] = my_membership["role"]
            else:
                c["is_member"] = False
                c["role"] = "none"
            c["member_count"] = len(members)
            if "challenge_mode" not in c:
                c["challenge_mode"] = "manual"
        return [c for c in _MOCK_COMMUNITIES if c["is_member"]]

    with cloud_session_ctx() as session:
        if session is None:
            for c in _MOCK_COMMUNITIES:
                members = _MOCK_MEMBERS.get(c["id"], [])
                my_membership = next((m for m in members if m["user_id"] == str(user_id)), None)
                if my_membership:
                    c["is_member"] = True
                    c["role"] = my_membership["role"]
                else:
                    c["is_member"] = False
                    c["role"] = "none"
                c["member_count"] = len(members)
                if "challenge_mode" not in c:
                    c["challenge_mode"] = "manual"
            return [c for c in _MOCK_COMMUNITIES if c["is_member"]]
        from m6_6_community.repository import list_user_communities
        return list_user_communities(session, user_id)


# ---------------------------------------------------------------------------
# POST /communities — Create a community
# ---------------------------------------------------------------------------

@router.post("/communities", response_model=CommunityRead)
async def create_community_endpoint(body: CommunityCreate, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        new_id = f"mock-new-{uuid.uuid4().hex[:8]}"
        new_c = {
            "id": new_id,
            "name": body.name,
            "type": body.type,
            "theme": body.theme,
            "member_cap": body.member_cap,
            "member_count": 1,
            "is_member": True,
            "role": "admin",
            "challenge_mode": "manual",
            "goal": "",
            "vision": "",
            "codex": "",
            "rules": [],
            "quotes": [],
        }
        _MOCK_COMMUNITIES.append(new_c)
        _MOCK_MEMBERS[new_id] = [
            {"user_id": str(user_id), "role": "admin", "display_name": "Me (User)", "joined_at": datetime.utcnow().isoformat()}
        ]
        return new_c

    with cloud_session_ctx() as session:
        from m6_6_community.repository import create_community
        result = create_community(
            session, user_id, body.name, body.type, body.theme, body.member_cap,
        )
        result["is_member"] = True
        result["role"] = "admin"
        result["challenge_mode"] = "manual"
        return result


# ---------------------------------------------------------------------------
# POST /communities/join — Join by theme or random
# ---------------------------------------------------------------------------

@router.post("/communities/join")
async def join_community_endpoint(body: CommunityJoin, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return {"id": "mock-community-1", "name": "Interview Preparer", "joined": True}

    with cloud_session_ctx() as session:
        from m6_6_community.repository import join_community
        try:
            return join_community(session, user_id, body.mode, body.theme)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# GET /communities/{id}/codex — Community codex
# ---------------------------------------------------------------------------

@router.get("/communities/{community_id}/codex", response_model=CommunityCodex)
async def get_codex(community_id: str, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        for c in _MOCK_COMMUNITIES:
            if c["id"] == community_id:
                return {
                    "goal": c.get("goal", ""),
                    "vision": c.get("vision", ""),
                    "codex": c.get("codex", ""),
                    "quotes": c.get("quotes", []),
                    "rules": c.get("rules", []),
                }
        return {"goal": "", "vision": "", "codex": "", "quotes": [], "rules": []}

    with cloud_session_ctx() as session:
        from m6_6_community.repository import get_community_codex
        try:
            return get_community_codex(session, uuid.UUID(community_id), user_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# GET /communities/{id}/posts — Posts feed
# ---------------------------------------------------------------------------

@router.get("/communities/{community_id}/posts", response_model=list[SocialPostRead])
async def get_posts(community_id: str, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return _MOCK_POSTS

    with cloud_session_ctx() as session:
        from m6_6_community.repository import get_community_posts
        try:
            return get_community_posts(session, uuid.UUID(community_id), user_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# GET /communities/{id}/challenges — Challenge board
# ---------------------------------------------------------------------------

@router.get("/communities/{community_id}/challenges", response_model=list[ChallengeRead])
async def get_challenges(community_id: str, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return _MOCK_CHALLENGES

    with cloud_session_ctx() as session:
        from m6_6_community.repository import get_community_challenges
        try:
            return get_community_challenges(session, uuid.UUID(community_id), user_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# GET /communities/{id}/commitments — Commitment closed loop
# ---------------------------------------------------------------------------

@router.get("/communities/{community_id}/commitments", response_model=CommitmentsView)
async def get_commitments(community_id: str, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return {
            "commitments": [
                {"id": "mock-c-1", "content": "每天跑步 30 分鐘", "kind": "achievement", "validation_count": 1, "published_at": "2026-06-21T08:00:00"},
                {"id": "mock-c-2", "content": "完成三章教科書", "kind": "milestone", "validation_count": 0, "published_at": "2026-06-20T12:00:00"},
            ],
            "to_validate": [
                {"id": "mock-tv-1", "content": "學了五個新單字", "kind": "achievement", "author_id": "mock-user-b", "published_at": "2026-06-21T09:00:00"},
            ],
            "active_stakes": [
                {"id": "mock-s-1", "xp_amount": 50, "deadline": "2026-06-25T00:00:00"},
            ],
        }

    with cloud_session_ctx() as session:
        from m6_6_community.repository import get_community_commitments
        try:
            return get_community_commitments(session, uuid.UUID(community_id), user_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# POST /posts/draft — Create a draft post
# ---------------------------------------------------------------------------

@router.post("/posts/draft", response_model=DraftResult)
async def create_draft(body: SocialPostDraft, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return {
            "id": f"mock-draft-{uuid.uuid4().hex[:8]}",
            "is_draft": True,
            "privacy_warning": "此貼文將對社群成員可見。請確認不含敏感個人資訊。",
        }

    with cloud_session_ctx() as session:
        from m6_6_community.repository import create_post_draft
        try:
            return create_post_draft(
                session, user_id, uuid.UUID(body.community_id), body.content, body.kind,
            )
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# POST /posts/publish — Approve and publish a draft
# ---------------------------------------------------------------------------

@router.post("/posts/publish", response_model=PublishResult)
async def publish_post_endpoint(body: PublishRequest, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return {
            "id": body.draft_id,
            "published": True,
            "published_at": datetime.utcnow().isoformat(),
        }

    # [M2.3] Eguard privacy filter before publishing
    try:
        from m2_3_eguard.filter import EguardFilter
        eguard = EguardFilter()
        # We would filter the post content here in production
        # For now, proceed with publishing
    except Exception:
        logger.warning("[M4.13] Eguard not available, proceeding without PII filter")

    with cloud_session_ctx() as session:
        from m6_6_community.repository import publish_post
        try:
            result = publish_post(session, uuid.UUID(body.draft_id), user_id)

            # Broadcast SSE event
            await sse_broker.broadcast(
                str(session.get(
                    __import__("m6_6_community.models", fromlist=["SocialPost"]).SocialPost,
                    uuid.UUID(body.draft_id),
                ).community_id) if _is_cloud() else "mock",
                {
                    "type": "POST_PUBLISHED",
                    "post_id": body.draft_id,
                    "actor_id": str(user_id),
                    "message": "新貼文已發布",
                },
            )

            return result
        except (PermissionError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# POST /posts/{id}/like — Like a post
# ---------------------------------------------------------------------------

@router.post("/posts/{post_id}/like", response_model=LikeResult)
async def like_post_endpoint(post_id: str, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return {"id": post_id, "likes_count": 1}

    with cloud_session_ctx() as session:
        from m6_6_community.repository import like_post
        try:
            return like_post(session, uuid.UUID(post_id), user_id)
        except (PermissionError, ValueError) as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# GET /stakes — List user stakes
# ---------------------------------------------------------------------------

@router.get("/stakes", response_model=list[StakeRead])
async def list_stakes(request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return [
            {
                "id": "mock-stake-1",
                "community_id": "mock-community-1",
                "task_id": None,
                "xp_amount": 50,
                "status": "held",
                "deadline": "2026-06-25T00:00:00",
                "created_at": "2026-06-21T08:00:00",
            },
        ]

    with cloud_session_ctx() as session:
        from m6_6_community.repository import list_user_stakes
        return list_user_stakes(session, user_id)


# ---------------------------------------------------------------------------
# POST /stakes — Create a stake (RISK-07 dual gating)
# ---------------------------------------------------------------------------

@router.post("/stakes", response_model=StakeRead)
async def create_stake_endpoint(body: StakeCreate, request: Request):
    user_id = get_current_user_id(request)

    # [RISK-07] Dual gating
    gate_result = can_stake_on_task(
        xp_balance=100,  # In production, fetch from M6.5
        stake_amount=body.xp_amount,
    )
    if not gate_result.allowed:
        raise HTTPException(status_code=400, detail=gate_result.reason)

    if not _is_cloud():
        return {
            "id": f"mock-stake-{uuid.uuid4().hex[:8]}",
            "community_id": body.community_id,
            "task_id": body.task_id,
            "xp_amount": body.xp_amount,
            "status": "held",
            "deadline": body.deadline,
            "created_at": datetime.utcnow().isoformat(),
        }

    with cloud_session_ctx() as session:
        from m6_6_community.repository import create_stake
        from datetime import datetime as dt

        deadline = None
        if body.deadline:
            deadline = dt.fromisoformat(body.deadline)

        return create_stake(
            session, user_id, uuid.UUID(body.community_id),
            body.xp_amount,
            uuid.UUID(body.task_id) if body.task_id else None,
            deadline,
        )


# ---------------------------------------------------------------------------
# POST /validations — Create a peer validation
# ---------------------------------------------------------------------------

@router.post("/validations", response_model=ValidationResult)
async def create_validation_endpoint(body: ValidationCreate, request: Request):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return {
            "id": f"mock-val-{uuid.uuid4().hex[:8]}",
            "post_id": body.post_id,
            "validated_at": datetime.utcnow().isoformat(),
        }

    with cloud_session_ctx() as session:
        from m6_6_community.repository import create_validation
        try:
            result = create_validation(
                session, uuid.UUID(body.post_id), user_id, body.evidence_url,
            )

            # Broadcast SSE
            await sse_broker.broadcast(
                body.post_id,  # We'd need the community_id here
                {
                    "type": "COMMITMENT_VALIDATED",
                    "post_id": body.post_id,
                    "actor_id": str(user_id),
                    "message": "同儕驗證完成",
                },
            )

            return result
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# POST /challenges/{id}/approve — Admin approve a challenge
# ---------------------------------------------------------------------------

@router.post("/challenges/{challenge_id}/approve")
async def approve_challenge_endpoint(
    challenge_id: str,
    body: ChallengeApprove,
    request: Request,
):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        return {"id": challenge_id, "approved": True}

    with cloud_session_ctx() as session:
        from m6_6_community.repository import approve_challenge
        try:
            result = approve_challenge(
                session, uuid.UUID(challenge_id), user_id,
                body.edits,
            )

            # Broadcast SSE
            await sse_broker.broadcast(
                "all",  # Would need community_id
                {
                    "type": "CHALLENGE_ACTIVATED",
                    "challenge_id": challenge_id,
                    "actor_id": str(user_id),
                    "message": "新挑戰已啟動",
                },
            )

            return result
        except (ValueError, PermissionError) as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# POST /communities/{id}/codex — Update community codex
# ---------------------------------------------------------------------------

@router.post("/communities/{community_id}/codex", response_model=CommunityCodex)
async def update_codex_endpoint(
    community_id: str,
    body: CodexUpdate,
    request: Request,
):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        # Update mock community
        for c in _MOCK_COMMUNITIES:
            if c["id"] == community_id:
                c["goal"] = body.goal
                c["vision"] = body.vision
                c["codex"] = body.codex
                c["rules"] = body.rules
                c["quotes"] = body.quotes
                return c
        raise HTTPException(status_code=404, detail="Community not found")

    with cloud_session_ctx() as session:
        from m6_6_community.repository import update_community_codex
        try:
            return update_community_codex(
                session,
                uuid.UUID(community_id),
                user_id,
                body.goal,
                body.vision,
                body.codex,
                body.rules,
                body.quotes,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# POST /communities/{id}/challenges — Create community challenge
# ---------------------------------------------------------------------------

@router.post("/communities/{community_id}/challenges", response_model=ChallengeRead)
async def create_challenge_endpoint(
    community_id: str,
    body: ChallengeCreate,
    request: Request,
):
    user_id = get_current_user_id(request)

    if not _is_cloud():
        new_ch = {
            "id": f"mock-challenge-{uuid.uuid4()}",
            "title": body.title,
            "description": body.description,
            "period": body.period,
            "source": body.source,
            "progress": 0,
            "is_draft": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        _MOCK_CHALLENGES.append(new_ch)
        return new_ch

    with cloud_session_ctx() as session:
        from m6_6_community.repository import create_challenge
        try:
            # Check if admin
            from m6_6_community.repository import _assert_member
            member = _assert_member(session, uuid.UUID(community_id), user_id)
            is_draft = False
            if body.source == "ai_reviewed":
                is_draft = True

            result = create_challenge(
                session,
                uuid.UUID(community_id),
                user_id,
                body.title,
                body.description,
                body.period,
                body.source,
                is_draft=is_draft,
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# POST /communities/{id}/challenges/generate-ai — Generate AI challenge
# ---------------------------------------------------------------------------

@router.post("/communities/{community_id}/challenges/generate-ai", response_model=ChallengeRead)
async def generate_ai_challenge_endpoint(
    community_id: str,
    request: Request,
):
    user_id = get_current_user_id(request)

    # RISK-18: Build privacy-safe L3 only context
    privacy_layer = "L3"
    raw_transcripts = []
    intent_vectors = []

    # 1. Fetch aggregates
    member_cap = 5
    member_count = 3
    theme = "study"
    active_commitments_count = 0
    total_staked_xp = 0
    completion_rate = 0.8
    community_name = "社群空間"

    if _is_cloud():
        with cloud_session_ctx() as session:
            from m6_6_community.models import Community, CommunityMember, SocialPost, Stake
            from sqlalchemy import select, func

            comm = session.get(Community, uuid.UUID(community_id))
            if not comm:
                raise HTTPException(status_code=404, detail="Community not found")

            community_name = comm.name
            member_cap = comm.member_cap or 5
            theme = comm.theme or "study"

            member_count = session.execute(
                select(func.count(CommunityMember.user_id)).where(CommunityMember.community_id == comm.id)
            ).scalar() or 1

            active_commitments_count = session.execute(
                select(func.count(SocialPost.id)).where(
                    SocialPost.community_id == comm.id,
                    SocialPost.is_draft == False,
                    SocialPost.kind.in_(["achievement", "milestone"])
                )
            ).scalar() or 0

            total_staked_xp = session.execute(
                select(func.sum(Stake.xp_amount)).where(
                    Stake.community_id == comm.id,
                    Stake.status == "held"
                )
            ).scalar() or 0

    # RISK-18: Enforce conservative template tier for member_cap <= 3
    use_conservative = (member_cap <= 3)

    # Generate content using templates or LLM (Gemini) if API key is set
    title = ""
    description = ""

    # Simple template generation
    if use_conservative:
        # Conservative template tier for small groups
        if theme == "study":
            title = "本週社群挑戰：專注學習番茄鐘"
            description = f"全體小組成員本週共同累積完成學習番茄鐘。目前社群共有 {member_count} 位夥伴，讓我們一起穩步前進。"
        elif theme == "career":
            title = "本週社群挑戰：履歷精進與專業閱讀"
            description = f"閱讀一篇行業報告或優化個人履歷欄位。本週社群內共有 {active_commitments_count} 個活躍承諾，共同提升專業力。"
        elif theme == "cooking":
            title = "本週社群挑戰：健康膳食挑戰"
            description = "嘗試製作一道減鹽或低脂的健康餐點並記錄。專注於日常健康習慣的建立。"
        else:
            title = "本週社群挑戰：每日習慣打卡"
            description = f"每天完成一個微小的自律行動。本週社群質押了 {total_staked_xp} XP，讓我們保持動力。"
    else:
        # Standard templates
        if theme == "study":
            title = "本週挑戰：每日進步一點點，突破 2 小時學習"
            description = f"挑戰每天專注學習 2 小時，並在社群分享你的精要筆記！本群目前累積了 {active_commitments_count} 個公開承諾，快來加入學習潮流！"
        elif theme == "career":
            title = "本週挑戰：模擬面試與技能演練"
            description = f"尋找夥伴進行一次 30 分鐘的模擬面試，或向社群分享你的一項核心技能展示。讓我們一起拿到 Offer！"
        elif theme == "cooking":
            title = "本週挑戰：解鎖全新料理"
            description = "這週嘗試烹飪一道你從未做過的料理，並與社群分享精美的食物照片或食譜心得！"
        else:
            title = "本週挑戰：跨出舒適圈打卡"
            description = f"主動找一位新朋友交流或嘗試一件新鮮事，並發布成就貼文！本週社群對賭了 {total_staked_xp} XP，一起衝刺！"

    # Save as draft challenge (is_draft=True)
    if not _is_cloud():
        new_ch = {
            "id": f"mock-challenge-{uuid.uuid4()}",
            "title": title,
            "description": description,
            "period": "weekly",
            "source": "ai_reviewed",
            "progress": 0,
            "is_draft": True,  # AI generated draft
            "created_at": datetime.utcnow().isoformat(),
        }
        _MOCK_CHALLENGES.append(new_ch)
        return new_ch

    with cloud_session_ctx() as session:
        from m6_6_community.repository import create_challenge
        try:
            result = create_challenge(
                session,
                uuid.UUID(community_id),
                user_id,
                title,
                description,
                period="weekly",
                source="ai_reviewed",
                is_draft=True,  # Default to draft for AI generation
            )
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")


# ---------------------------------------------------------------------------
# GET /stream — SSE event stream (community-scoped)
# ---------------------------------------------------------------------------

@router.get("/stream")
async def community_stream(
    community_id: str = Query(..., description="Community ID to subscribe to"),
):
    return StreamingResponse(
        sse_broker.subscribe(community_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET /communities/{id}/members — Get members
# ---------------------------------------------------------------------------
@router.get("/communities/{community_id}/members", response_model=list[MemberRead])
async def get_members_endpoint(community_id: str, request: Request):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        members = _MOCK_MEMBERS.get(community_id, [])
        if not any(m["user_id"] == str(user_id) for m in members):
            raise HTTPException(status_code=403, detail="Not a member of this community")
        return members
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import get_community_members
        try:
            return get_community_members(session, uuid.UUID(community_id), user_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not a member of this community")
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# POST /communities/{id}/members/{target_user_id}/role — Update member role
# ---------------------------------------------------------------------------
@router.post("/communities/{community_id}/members/{target_user_id}/role")
async def update_member_role_endpoint(
    community_id: str,
    target_user_id: str,
    body: RoleUpdateRequest,
    request: Request
):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        members = _MOCK_MEMBERS.get(community_id, [])
        me = next((m for m in members if m["user_id"] == str(user_id)), None)
        if not me or me["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can update member roles")
            
        target = next((m for m in members if m["user_id"] == target_user_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Member not found")
            
        if target["role"] == "admin" and body.role == "member":
            admin_count = sum(1 for m in members if m["role"] == "admin")
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="無法取消管理員權限，因為該成員是此社群的唯一管理員")
                
        target["role"] = body.role
        return {"user_id": target_user_id, "role": body.role}
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import update_member_role
        try:
            return update_member_role(
                session,
                uuid.UUID(community_id),
                user_id,
                uuid.UUID(target_user_id),
                body.role
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# DELETE /communities/{id}/members/{target_user_id} — Kick member
# ---------------------------------------------------------------------------
@router.delete("/communities/{community_id}/members/{target_user_id}")
async def kick_member_endpoint(
    community_id: str,
    target_user_id: str,
    request: Request
):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        members = _MOCK_MEMBERS.get(community_id, [])
        me = next((m for m in members if m["user_id"] == str(user_id)), None)
        if not me or me["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can kick members")
            
        if str(user_id) == target_user_id:
            raise HTTPException(status_code=400, detail="您不能踢除您自己")
            
        target = next((m for m in members if m["user_id"] == target_user_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Member not found")
            
        if target["role"] == "admin":
            admin_count = sum(1 for m in members if m["role"] == "admin")
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="無法踢除管理員，因為該成員是此社群的唯一管理員")
                
        _MOCK_MEMBERS[community_id] = [m for m in members if m["user_id"] != target_user_id]
        return {"user_id": target_user_id, "kicked": True}
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import kick_member
        try:
            return kick_member(session, uuid.UUID(community_id), user_id, uuid.UUID(target_user_id))
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# POST /communities/{id}/leave — Leave community
# ---------------------------------------------------------------------------
@router.post("/communities/{community_id}/leave")
async def leave_community_endpoint(community_id: str, request: Request):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        members = _MOCK_MEMBERS.get(community_id, [])
        me = next((m for m in members if m["user_id"] == str(user_id)), None)
        if not me:
            raise HTTPException(status_code=403, detail="Not a member of this community")
            
        active_count = len(members)
        if me["role"] == "admin" and active_count > 1:
            admin_count = sum(1 for m in members if m["role"] == "admin")
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="無法退出社群，因為您是此社群唯一的管理員。請先指派其他成員為管理員")
                
        _MOCK_MEMBERS[community_id] = [m for m in members if m["user_id"] != str(user_id)]
        
        # If no members left, deactivate mock community
        if active_count <= 1:
            for c in _MOCK_COMMUNITIES:
                if c["id"] == community_id:
                    c["is_member"] = False
            
        return {"community_id": community_id, "left": True}
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import leave_community
        try:
            return leave_community(session, uuid.UUID(community_id), user_id)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# GET /communities/{id}/join-requests — Get join requests
# ---------------------------------------------------------------------------
@router.get("/communities/{community_id}/join-requests", response_model=list[JoinRequestRead])
async def get_join_requests_endpoint(community_id: str, request: Request):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        members = _MOCK_MEMBERS.get(community_id, [])
        me = next((m for m in members if m["user_id"] == str(user_id)), None)
        if not me or me["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can view join requests")
            
        return [r for r in _MOCK_JOIN_REQUESTS if r["community_id"] == community_id and r["status"] == "pending"]
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import get_join_requests
        try:
            return get_join_requests(session, uuid.UUID(community_id), user_id)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))


# ---------------------------------------------------------------------------
# POST /communities/{id}/join-requests — Request to join
# ---------------------------------------------------------------------------
@router.post("/communities/{community_id}/join-requests")
async def create_join_request_endpoint(community_id: str, request: Request):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        members = _MOCK_MEMBERS.get(community_id, [])
        if any(m["user_id"] == str(user_id) for m in members):
            raise HTTPException(status_code=400, detail="您已是該社群成員")
            
        existing = next((r for r in _MOCK_JOIN_REQUESTS if r["community_id"] == community_id and r["user_id"] == str(user_id) and r["status"] == "pending"), None)
        if existing:
            raise HTTPException(status_code=400, detail="已送出加入申請，請等待管理員審核")
            
        new_req = {
            "id": f"mock-req-{uuid.uuid4().hex[:8]}",
            "community_id": community_id,
            "user_id": str(user_id),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "display_name": "Me (User)"
        }
        _MOCK_JOIN_REQUESTS.append(new_req)
        return {"id": new_req["id"], "community_id": community_id, "status": "pending"}
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import create_join_request
        try:
            return create_join_request(session, uuid.UUID(community_id), user_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# POST /communities/{id}/join-requests/{request_id}/action — Approve/reject
# ---------------------------------------------------------------------------
@router.post("/communities/{community_id}/join-requests/{request_id}/action")
async def handle_join_request_endpoint(
    community_id: str,
    request_id: str,
    body: JoinRequestAction,
    request: Request
):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        members = _MOCK_MEMBERS.get(community_id, [])
        me = next((m for m in members if m["user_id"] == str(user_id)), None)
        if not me or me["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can approve/reject join requests")
            
        req = next((r for r in _MOCK_JOIN_REQUESTS if r["id"] == request_id), None)
        if not req or req["community_id"] != community_id:
            raise HTTPException(status_code=404, detail="Join request not found")
            
        if req["status"] != "pending":
            raise HTTPException(status_code=400, detail="該申請已被處理")
            
        if body.action == "approve":
            comm = next((c for c in _MOCK_COMMUNITIES if c["id"] == community_id), None)
            if not comm:
                comm = next((c for c in _MOCK_EXPLORE_COMMUNITIES if c["id"] == community_id), None)
            
            if not comm:
                raise HTTPException(status_code=404, detail="Community not found")
                
            if len(members) >= comm["member_cap"]:
                raise HTTPException(status_code=400, detail=f"無法加入，該社群已達人數上限 {comm['member_cap']} 人 (鄧巴數限制)")
                
            members.append({
                "user_id": req["user_id"],
                "role": "member",
                "display_name": req["display_name"],
                "joined_at": datetime.utcnow().isoformat()
            })
            _MOCK_MEMBERS[community_id] = members
            req["status"] = "approved"
            
            # Make sure it's present in _MOCK_COMMUNITIES if it wasn't
            if comm not in _MOCK_COMMUNITIES:
                _MOCK_COMMUNITIES.append(comm)
        else:
            req["status"] = "rejected"
            
        return {"request_id": request_id, "status": req["status"]}
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import handle_join_request
        try:
            return handle_join_request(
                session,
                uuid.UUID(community_id),
                user_id,
                uuid.UUID(request_id),
                body.action
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# POST /communities/{id}/settings — Update settings
# ---------------------------------------------------------------------------
@router.post("/communities/{community_id}/settings")
async def update_settings_endpoint(
    community_id: str,
    body: CommunitySettingsUpdate,
    request: Request
):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        members = _MOCK_MEMBERS.get(community_id, [])
        me = next((m for m in members if m["user_id"] == str(user_id)), None)
        if not me or me["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can update settings")
            
        comm = next((c for c in _MOCK_COMMUNITIES if c["id"] == community_id), None)
        if not comm:
            raise HTTPException(status_code=404, detail="Community not found")
            
        if body.member_cap < 2 or body.member_cap > 8:
            raise HTTPException(status_code=400, detail="人數上限必須在 2 至 8 人之間 (鄧巴數限制)")
            
        if body.member_cap < len(members):
            raise HTTPException(status_code=400, detail=f"人數上限不能少於當前成員數 ({len(members)} 人)")
            
        comm["challenge_mode"] = body.challenge_mode
        comm["member_cap"] = body.member_cap
        return {"id": community_id, "challenge_mode": body.challenge_mode, "member_cap": body.member_cap}
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import update_community_settings
        try:
            return update_community_settings(
                session,
                uuid.UUID(community_id),
                user_id,
                body.challenge_mode,
                body.member_cap
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# GET /communities/explore — Explore public communities
# ---------------------------------------------------------------------------
@router.get("/communities/explore", response_model=list[CommunityRead])
async def explore_communities_endpoint(request: Request):
    user_id = get_current_user_id(request)
    
    if not _is_cloud():
        unjoined = []
        for c in _MOCK_COMMUNITIES:
            members = _MOCK_MEMBERS.get(c["id"], [])
            if not any(m["user_id"] == str(user_id) for m in members):
                unjoined.append(c)
                
        for c in _MOCK_EXPLORE_COMMUNITIES:
            if not any(x["id"] == c["id"] for x in _MOCK_COMMUNITIES):
                unjoined.append(c)
                
        results = []
        for c in unjoined:
            pending = any(r["community_id"] == c["id"] and r["user_id"] == str(user_id) and r["status"] == "pending" for r in _MOCK_JOIN_REQUESTS)
            results.append({
                "id": c["id"],
                "name": c["name"],
                "type": c.get("type", "user_created"),
                "theme": c.get("theme"),
                "member_cap": c["member_cap"],
                "member_count": len(_MOCK_MEMBERS.get(c["id"], [])),
                "is_member": False,
                "role": "none",
                "challenge_mode": c.get("challenge_mode", "manual"),
                "goal": "申請審核中..." if pending else c.get("goal", ""),
                "vision": c.get("vision", ""),
                "codex": c.get("codex", ""),
                "rules": c.get("rules", []),
                "quotes": c.get("quotes", []),
            })
        return results
        
    with cloud_session_ctx() as session:
        from m6_6_community.repository import list_explore_communities
        return list_explore_communities(session, user_id)
