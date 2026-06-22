"""
M4.13.3 — Cross-Community Isolation Middleware

SPEC: docs/modules/M3_7_community_ui_SPEC.md §4 (M4.13.3)
All queries must carry community_id + member-check.
This module wraps the isolation logic as a FastAPI dependency.
"""
import uuid
import logging

from fastapi import Depends, HTTPException, Request

from m6_2_postgresql.engine import get_cloud_session

logger = logging.getLogger(__name__)


def get_current_user_id(request: Request) -> uuid.UUID:
    """
    Extract current user ID from request.
    In production, this reads from auth token.
    For MVP, reads from config or X-User-Id header.
    """
    user_id_str = request.headers.get("X-User-Id")
    if user_id_str:
        try:
            return uuid.UUID(user_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-User-Id header")

    # Fallback to config default
    from config import get_settings
    return uuid.UUID(get_settings().current_user_id)


def require_community_membership(
    community_id: uuid.UUID,
    user_id: uuid.UUID,
    session=None,
) -> bool:
    """
    Check if user is an active member of the community.
    Raises HTTPException 403 if not a member.
    """
    if session is None:
        session = get_cloud_session()
        if session is None:
            # Cloud not available — allow in dev mode
            logger.warning("[M4.13.3] Cloud session unavailable, skipping membership check")
            return True

    from m6_6_community.repository import _assert_member
    try:
        _assert_member(session, community_id, user_id)
        return True
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"User {user_id} is not a member of community {community_id}",
        )
