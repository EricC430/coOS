import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from .db import get_db
from .models import (
    HiddenAchievementModel,
    UserAchievementModel,
    EpistemicEvidenceQueueModel,
)
from .schemas import (
    AchievementWallResponse,
    UnlockedAchievementItem,
    AckAchievementRequest,
    AckAchievementResponse,
    QueueStatusResponse,
    ArchetypeEnum,
    RarityEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["m4_12_hidden_achievement"])


# ---------------------------------------------------------------------------
# WebSocket Manager for Surprise Notifications
# ---------------------------------------------------------------------------
class SurpriseConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"[M4.12 WS] User {user_id} connected. Active: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"[M4.12 WS] User {user_id} disconnected.")

    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"[M4.12 WS] Failed to send message to user {user_id}: {e}")


ws_manager = SurpriseConnectionManager()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/api/achievements", response_model=AchievementWallResponse)
def get_user_achievements(
    user_id: str = Query(..., description="使用者 ID"),
    role_id: Optional[str] = Query(None, description="作用角色過濾 (可選)"),
    db: Session = Depends(get_db),
):
    """
    查詢已解鎖之成就總覽 (嚴格遵循 M3.11.3 絕對無 UI 狀態與零洩漏鐵律).
    SQL 層強制過濾:
      WHERE is_hidden = 0
         OR (is_hidden = 1 AND id IN (SELECT achievement_id FROM user_achievements WHERE user_id = :uid))
    未解鎖之隱藏成就 0% 回傳至客戶端。
    """
    from sqlalchemy import or_, select

    unlocked_subquery = select(UserAchievementModel.achievement_id).filter(
        UserAchievementModel.user_id == user_id
    )

    query = (
        db.query(UserAchievementModel, HiddenAchievementModel)
        .join(HiddenAchievementModel, UserAchievementModel.achievement_id == HiddenAchievementModel.id)
        .filter(
            UserAchievementModel.user_id == user_id,
            or_(
                HiddenAchievementModel.is_hidden == False,
                HiddenAchievementModel.id.in_(unlocked_subquery),
            ),
        )
    )

    if role_id:
        # 若指定 role_id，可過濾或優先排序，但成就仍全域有效
        pass

    results = query.all()

    items: List[UnlockedAchievementItem] = []
    for user_ach, ach in results:
        items.append(
            UnlockedAchievementItem(
                id=ach.id,
                archetype=ArchetypeEnum(ach.archetype),
                name=ach.name,
                description=ach.description,
                flavor_text=user_ach.context_summary or ach.flavor_text_template,
                rarity=RarityEnum(ach.rarity),
                exp_reward=user_ach.xp_awarded or ach.exp_reward,
                badge_icon_url=ach.badge_icon_url,
                origin_role_id=user_ach.origin_role_id,
                unlocked_at=user_ach.unlocked_at,
                is_new=not user_ach.is_acknowledged,
                context_summary=user_ach.context_summary,
            )
        )

    # FR-006: 排除未解鎖隱藏成就後的總可見數 (分母)
    # 公開成就總數 + 該使用者已解鎖的隱藏成就總數 (避免解鎖公開成就時被雙重累計)
    public_count = (
        db.query(HiddenAchievementModel)
        .filter(HiddenAchievementModel.is_hidden == False)
        .count()
    )
    unlocked_hidden_count = sum(1 for user_ach, ach in results if ach.is_hidden)
    total_visible = public_count + unlocked_hidden_count

    return AchievementWallResponse(
        user_id=user_id,
        total_unlocked_count=len(items),
        total_visible_count=total_visible,
        items=items,
    )


@router.post("/api/achievements/ack", response_model=AckAchievementResponse)
def acknowledge_surprise_modal(
    req: AckAchievementRequest,
    db: Session = Depends(get_db),
):
    """
    客戶端關閉或標記 SurpriseModal 為已讀後呼叫，將 is_acknowledged 置為 1。
    """
    updated_count = (
        db.query(UserAchievementModel)
        .filter(
            UserAchievementModel.user_id == req.user_id,
            UserAchievementModel.achievement_id.in_(req.achievement_ids),
        )
        .update({"is_acknowledged": True}, synchronize_session=False)
    )
    db.commit()
    return AckAchievementResponse(success=True, acknowledged_count=updated_count)


@router.get("/api/m4_12/queue/status", response_model=QueueStatusResponse)
def get_evidence_queue_status(db: Session = Depends(get_db)):
    """
    查詢離線特徵佐證暫存佇列狀態 (可觀測性與健康診斷).
    """
    pending = (
        db.query(EpistemicEvidenceQueueModel)
        .filter(EpistemicEvidenceQueueModel.status == "PENDING")
        .count()
    )
    processing = (
        db.query(EpistemicEvidenceQueueModel)
        .filter(EpistemicEvidenceQueueModel.status == "PROCESSING")
        .count()
    )
    failed = (
        db.query(EpistemicEvidenceQueueModel)
        .filter(EpistemicEvidenceQueueModel.status == "FAILED")
        .count()
    )
    return QueueStatusResponse(
        pending_count=pending,
        processing_count=processing,
        failed_count=failed,
    )


@router.websocket("/api/m4_12/ws")
async def websocket_surprise_endpoint(
    websocket: WebSocket,
    user_id: str = Query("user_default"),
):
    """
    WebSocket 長連線端點，負責推送無預警 SurpriseModal 事件並處理 ACK.
    開機/重連時若有積壓未確認成就，執行 Single Cap (至多推播 1 筆最高稀有度).
    使用短生命週期 SessionLocal 避免長連線佔用連線資源與造成狀態陳舊。
    """
    await ws_manager.connect(user_id, websocket)
    try:
        from .db import SessionLocal
        from .service import HiddenAchievementService

        # 斷線重連或開機補發檢查 (FR-015 Single Cap)
        with SessionLocal() as session:
            service = HiddenAchievementService(db_session=session, ws_manager=ws_manager)
            await service.handle_reconnect_catch_up(user_id)

        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if payload.get("action") == "ACK_SURPRISE_MODAL":
                    ach_id = payload.get("achievement_id")
                    if ach_id:
                        with SessionLocal() as session:
                            service = HiddenAchievementService(db_session=session, ws_manager=ws_manager)
                            service.acknowledge_achievement(user_id, ach_id)
            except Exception as e:
                logger.warning(f"[M4.12 WS] Invalid message format: {e}")
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)
    except Exception as e:
        logger.error(f"[M4.12 WS] Connection error: {e}")
        ws_manager.disconnect(user_id, websocket)

