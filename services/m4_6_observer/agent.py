"""
M4.6 -- Observer Agent 主節點

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md §7.1
研究依據: [R10 §代理工作流 + R02 §動態狀態解碼]

[決策] 30s timeout — 超時靜默失敗以適應本地端推論（SPEC §7.1 / §9）。
[RISK-12] 萃取結果經 Eguard 過濾；自動偵測成就預設 visibility="private"。
[RISK-08] 推論 desire 不直接注入 Persona，走 bdi_bridge。
[RISK-06] 萃取結果綁定當前 role_id。

設計：observer_extract 是 timeout 包裝；run_observer 是同步友善的一次性萃取入口，
      接受注入式 db / eguard / sse 以利測試（不依賴 live Gemma / live DB）。
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .emotion import detect_emotion
from .project_detector import detect_and_upsert_project

logger = logging.getLogger(__name__)

OBSERVER_TIMEOUT_SECS = 30.0


@dataclass
class ObserverResult:
    project_name: str | None = None
    extracted_intent: str | None = None
    time_commitment: str | None = None
    achievement: dict | None = None
    # v1.2 新增
    promises_detected: list[dict] = field(default_factory=list)
    goal_established: dict | None = None
    session_intention: str | None = None
    emotion_detected: str | None = None  # [決策] 當下情緒標籤
    role_id: str = ""
    timed_out: bool = False
    elapsed_seconds: float = 0.0

    @property
    def extraction(self) -> dict:
        """供 RISK-12 測試檢查整體萃取結果不含 PII。"""
        return {
            "project_name": self.project_name,
            "extracted_intent": self.extracted_intent,
            "emotion_detected": self.emotion_detected,
            "achievement": self.achievement,
        }


# ── 意圖 / 成就 規則 ────────────────────────────────────────────────────────
_DEADLINE_PATTERNS = [
    r"(?:明天|後天|今晚|下週|這週|月底|週[一二三四五六日])",
    r"(?:要交|截止|deadline|趕完|來不及)",
]
_STREAK_PATTERN = re.compile(r"連續.*?(\d+)\s*天")


def _extract_intent(user_msg: str) -> str | None:
    """規則層意圖萃取：偵測時間壓力 -> 'deadline_urgent'。"""
    hits = sum(1 for p in _DEADLINE_PATTERNS if re.search(p, user_msg))
    if hits >= 2:
        return "deadline_urgent"
    if hits == 1 and re.search(r"(?:要交|截止|deadline|趕完|來不及)", user_msg):
        return "deadline"
    return None


def _detect_achievement(user_msg: str) -> dict | None:
    """[RISK-12] 自動偵測成就，預設 visibility='private'。"""
    m = _STREAK_PATTERN.search(user_msg)
    if m:
        return {
            "type": "streak",
            "days": int(m.group(1)),
            "default_visibility": "private",  # [RISK-12] 預設不公開
        }
    return None


# ---------------------------------------------------------------------------
# 一次性萃取 (測試與 dispatch 共用)
# ---------------------------------------------------------------------------

async def _do_extraction(
    user_msg: str,
    role_id: str,
    db: Any,
    eguard: Any,
    sse: Any,
    gemma: Any = None,
    thread_id: str = "",
    persona_id: str = "",
    current_active_project: str | None = None,
    expert_name: str | None = None,
) -> ObserverResult:
    """執行所有萃取步驟。慢/失敗的子步驟不應拖垮整體（由上層 timeout 守護）。"""
    result = ObserverResult(role_id=role_id)

    # 1. 主題標籤偵測 + upsert (Regex -> LLM fallback -> Eguard -> 去重 -> SSE)
    #    [測試回饋] 傳入當前活躍專案，相同則不重複標記
    result.project_name = await detect_and_upsert_project(
        user_msg, role_id=role_id, db=db, eguard=eguard, sse=sse, gemma=gemma,
        current_active_project=current_active_project,
        source="chat",
        expert_name=expert_name,
    )

    # 2. 意圖萃取
    result.extracted_intent = _extract_intent(user_msg)

    # 3. 情緒萃取 [決策]
    result.emotion_detected = detect_emotion(user_msg)

    # 4. 成就偵測 [RISK-12 預設 private]
    result.achievement = _detect_achievement(user_msg)

    # 5. v1.2: 承諾萃取 (LLM)
    if gemma and thread_id:
        from .promise_extractor import extract_promises
        result.promises_detected = await extract_promises(
            user_msg, thread_id, role_id, persona_id, gemma, eguard, db, sse
        )

    # 6. v1.2: 目標確立偵測 (LLM)
    if gemma and persona_id:
        from .goal_detector import detect_goal_establishment
        # Fetch existing goals for dedup
        rows = await db.fetch_all("SELECT title FROM goals WHERE role_id = :rid", {"rid": role_id})
        existing_goals = [dict(r) for r in rows]

        # We need assistant_msg; for now we only have user_msg in this call.
        # Goal detector might need the conversation history or just user intent.
        # In this MVP, we pass empty string for assistant_msg or skip if not available.
        result.goal_established = await detect_goal_establishment(
            user_msg, "", thread_id, role_id, persona_id, existing_goals, gemma, eguard, db, sse
        )

    return result


async def run_observer(
    user_msg: str,
    role_id: str,
    db: Any,
    eguard: Any,
    sse: Any,
    gemma: Any = None,
    thread_id: str = "",
    persona_id: str = "",
    timeout: float = OBSERVER_TIMEOUT_SECS,
    current_active_project: str | None = None,
    expert_name: str | None = None,
) -> ObserverResult:
    """
    一次性背景萃取入口。
    """
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(
            _do_extraction(
                user_msg, role_id, db, eguard, sse,
                gemma=gemma, thread_id=thread_id, persona_id=persona_id,
                current_active_project=current_active_project,
                expert_name=expert_name,
            ),
            timeout=timeout,
        )
    except Exception as e:
        logger.warning("[M4.6] observer_failed or timeout role=%s: %s", role_id, e)
        return ObserverResult(role_id=role_id, timed_out=True,
                              elapsed_seconds=time.monotonic() - start)
    result.elapsed_seconds = time.monotonic() - start
    return result



async def observer_extract(
    task: dict,
    _impl: Callable[[dict], Awaitable[ObserverResult]] | None = None,
    timeout: float = OBSERVER_TIMEOUT_SECS,
) -> ObserverResult:
    """
    [R10 §代理工作流] 非同步萃取的 timeout 包裝，不阻塞 Persona。
    [決策] 超時靜默失敗 -> timed_out=True。
    """
    async def real_impl(t: dict) -> ObserverResult:
        from services.main import _db_adapter, _eguard_filter
        return await _do_extraction(
            user_msg=t.get("user_message", ""),
            role_id=t.get("role_id", ""),
            db=_db_adapter,
            eguard=_eguard_filter,
            sse=None # SSE will be implemented in Phase 3
        )

    impl = _impl or real_impl
    try:
        return await asyncio.wait_for(impl(task), timeout=timeout)
    except TimeoutError:
        logger.warning("[M4.6] observer_timeout thread=%s", task.get("thread_id"))
        return ObserverResult(timed_out=True)


async def _noop_impl(task: dict) -> ObserverResult:  # pragma: no cover - default placeholder
    return ObserverResult(role_id=task.get("role_id", ""))
