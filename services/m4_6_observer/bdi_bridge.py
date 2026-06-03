"""
M4.6 -- BDI 整合介面

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md §7.3
研究依據: [R09 §6.2 BDI]

[RISK-08] Observer 推論的 desire 必須經 BDI Reconciler 整合為 intention 後才供 M4.2 使用。
          絕不可直接把 desire 欄位丟給 Persona prompt（會與 ToM belief 矛盾，產生衝突建議）。

本模組只負責把 desire 投遞到 BDI 佇列；整合邏輯在 M4.2 的 reconcile_bdi。
"""
from __future__ import annotations

import asyncio
from typing import Any


class BDIQueue:
    """簡單的非同步佇列封裝，供 Observer -> M4.2 BDI Reconciler 解耦傳遞。"""

    def __init__(self) -> None:
        self._q: asyncio.Queue[dict] = asyncio.Queue()

    async def put(self, item: dict) -> None:
        await self._q.put(item)

    async def get(self) -> dict:
        return await self._q.get()

    def empty(self) -> bool:
        return self._q.empty()


async def submit_to_bdi_reconciler(
    desire: str,
    thread_id: str,
    role_id: str,
    queue: Any,
) -> None:
    """
    [RISK-08] 將 Observer 推論的表面 desire 投遞至 BDI 佇列。

    M4.2 的 BDI Reconciler 會從此佇列取出，與 belief 整合為 intention 後才注入 Persona。
    """
    await queue.put(
        {
            "source": "M4.6",
            "desire": desire,
            "thread_id": thread_id,
            "role_id": role_id,
        }
    )
