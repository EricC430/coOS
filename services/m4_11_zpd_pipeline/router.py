from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .db import get_db
from .schemas import (
    AcceptChallengeRequest,
    AcceptChallengeResponse,
    ActiveChallengeResponse,
    CompleteChallengeRequest,
    CompleteChallengeResponse,
    DrawChallengeRequest,
    ZPDChallengeDTO,
)
from .service import ZPDPipelineService

router = APIRouter(prefix="/api/m4_11", tags=["m4_11_zpd"])


def get_zpd_service(db: Session = Depends(get_db)) -> ZPDPipelineService:
    return ZPDPipelineService(db_session=db)


@router.post(
    "/draw_challenge",
    response_model=ZPDChallengeDTO,
    summary="抽取符合 ZPD 邊界之動態挑戰任務",
)
async def draw_challenge(
    request: DrawChallengeRequest,
    service: ZPDPipelineService = Depends(get_zpd_service),
):
    try:
        challenge = service.draw_challenge(
            user_id=request.user_id,
            role_id=request.role_id,
            force_fallback=request.force_fallback,
        )
        return challenge
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to draw challenge: {str(e)}",
        )


@router.get(
    "/active_challenge",
    response_model=ActiveChallengeResponse,
    summary="取得當前角色進行中的 ZPD 挑戰",
)
async def get_active_challenge(
    role_id: str = Query(...),
    user_id: str = Query(default="default_user"),
    service: ZPDPipelineService = Depends(get_zpd_service),
):
    active = service.get_active_challenge(user_id=user_id, role_id=role_id)
    return ActiveChallengeResponse(active_challenge=active)


@router.post(
    "/accept_challenge",
    response_model=AcceptChallengeResponse,
    summary="接受並啟用抽取的挑戰任務 (單一槽位)",
)
async def accept_challenge(
    request: AcceptChallengeRequest,
    service: ZPDPipelineService = Depends(get_zpd_service),
):
    try:
        active = service.accept_challenge(
            challenge_id=request.challenge_id,
            replace_existing=request.replace_existing,
        )
        return AcceptChallengeResponse(success=True, active_challenge=active)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept challenge: {str(e)}",
        )


@router.post(
    "/complete_challenge",
    response_model=CompleteChallengeResponse,
    summary="提交自我申報反思並結算 XP (經 M6.5 Gatekeeper)",
)
async def complete_challenge(
    request: CompleteChallengeRequest,
    service: ZPDPipelineService = Depends(get_zpd_service),
):
    try:
        result = service.complete_challenge(
            challenge_id=request.challenge_id,
            user_feeling=request.user_feeling,
            user_action_plan=request.user_action_plan,
            actual_minutes=request.actual_minutes,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete challenge: {str(e)}",
        )
