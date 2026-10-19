import logging
from typing import Dict, List, Optional

from .schemas import UnlockEventPayload

logger = logging.getLogger(__name__)


class SurpriseDispatcher:
    """
    心流感知無預警驚喜派發器 (M4.12.3 & RISK-04).
    於使用者處於高認知負荷 (M4.8) 或高速輸入編程期間暫存成就事件，
    僅於 M1.2 微斷點（如停頓沉思、對話回合交接、反思提交）時進行 WebSocket 廣播。
    """

    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self._flow_states: Dict[str, bool] = {}
        self._pending_queues: Dict[str, List[UnlockEventPayload]] = {}

    def set_flow_state(self, user_id: str, is_in_flow: bool):
        """更新使用者當前心流負荷狀態 (來自 M4.8 / 前端焦點信號)."""
        self._flow_states[user_id] = is_in_flow
        logger.debug(f"[M4.12 Dispatcher] User {user_id} flow state updated: in_flow={is_in_flow}")

    def is_in_flow(self, user_id: str) -> bool:
        return self._flow_states.get(user_id, False)

    def get_pending_surprises(self, user_id: str) -> List[UnlockEventPayload]:
        return self._pending_queues.get(user_id, [])

    async def queue_or_dispatch(
        self, user_id: str, payload: UnlockEventPayload
    ) -> bool:
        """
        若使用者正在深層心流中，暫存至佇列不打擾；
        若處於正常/閒置狀態，則立即派發 WebSocket 廣播。
        """
        if self.is_in_flow(user_id):
            if user_id not in self._pending_queues:
                self._pending_queues[user_id] = []
            self._pending_queues[user_id].append(payload)
            logger.info(
                f"[M4.12 Dispatcher] User {user_id} is in flow. Achievement {payload.achievement_id} queued."
            )
            return False

        await self._dispatch(user_id, payload)
        return True

    async def handle_micro_breakpoint(
        self, user_id: str
    ) -> List[UnlockEventPayload]:
        """
        接收到 M1.2 微斷點信號時呼叫，出隊並廣播所有暫存的成就驚喜.
        """
        self.set_flow_state(user_id, is_in_flow=False)
        queued = self._pending_queues.pop(user_id, [])
        if not queued:
            return []

        logger.info(
            f"[M4.12 Dispatcher] M1.2 micro-breakpoint hit for {user_id}. Releasing {len(queued)} surprises."
        )
        for payload in queued:
            await self._dispatch(user_id, payload)

        return queued

    async def _dispatch(self, user_id: str, payload: UnlockEventPayload):
        if self.ws_manager:
            await self.ws_manager.broadcast_to_user(
                user_id, payload.model_dump(mode="json")
            )
            logger.info(
                f"[M4.12 Dispatcher] Broadcasted {payload.achievement_id} to user {user_id}."
            )
