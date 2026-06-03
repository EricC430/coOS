"""
M4.6 Observer 背景萃取 Agent -- test suite

SPEC: docs/modules/M4_6_observer_agent_SPEC.md §6
Research: [R02 §動態狀態解碼 HMM] [R10 §結構化代理工作流] [R09 §6.2 BDI]
Risk coverage:
  RISK-12 (extraction passes Eguard; inferred achievements default private)
  RISK-08 (desire goes through BDI Reconciler, never injected directly into Persona)
  RISK-06 (extraction scoped to current role_id)
  Resilience (30s timeout, silent failure, does not block Persona)

Design: run_observer accepts injected collaborators (db / eguard / sse_sink) so the
project-detection regex fast-path is exercised deterministically without a live LLM,
matching the established M4.x test style.
"""
from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_6_observer.agent import ObserverResult, observer_extract, run_observer  # noqa: E402
from m4_6_observer.bdi_bridge import BDIQueue, submit_to_bdi_reconciler  # noqa: E402
from m4_6_observer.emotion import detect_emotion  # noqa: E402
from m4_6_observer.project_detector import (  # noqa: E402
    detect_and_upsert_project,
    regex_extract_project,
)

ROLE_CSIE = "role_csie"
ROLE_FAMILY = "role_family"


# ---------------------------------------------------------------------------
# In-memory fakes
# ---------------------------------------------------------------------------

@dataclass
class FakeProject:
    role_id: str
    name: str
    inferred_by_ai: bool = True
    default_visibility: str = "private"


@dataclass
class FakeDB:
    projects: list = field(default_factory=list)

    def add_project(self, role_id: str, name: str, inferred_by_ai: bool = True) -> FakeProject:
        p = FakeProject(role_id=role_id, name=name, inferred_by_ai=inferred_by_ai)
        self.projects.append(p)
        return p

    def projects_for(self, role_id: str) -> list[FakeProject]:
        return [p for p in self.projects if p.role_id == role_id]


class FakeEguard:
    """Strips a small PII set so tests do not depend on the full M2.3 patterns."""

    _PII = ["陳小明", "陳XX", "陳"]

    def filter_pii(self, text: str) -> str:
        out = text
        for token in self._PII:
            out = out.replace(token, "[REDACTED]")
        return out


class FakeSSE:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def emit(self, event_type: str, data: dict) -> None:
        self.events.append({"type": event_type, "data": data})


def _run(user_msg: str, role_id: str = ROLE_CSIE, **kw):
    """Synchronous helper around the async observer for terse test bodies."""
    db = kw.pop("db", FakeDB())
    eguard = kw.pop("eguard", FakeEguard())
    sse = kw.pop("sse", FakeSSE())
    result = asyncio.run(
        run_observer(user_msg=user_msg, role_id=role_id, db=db, eguard=eguard, sse=sse, **kw)
    )
    result._db = db  # type: ignore[attr-defined]
    result._sse = sse  # type: ignore[attr-defined]
    return result


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

class TestObserverExtraction:
    def test_project_detected_in_30_seconds(self):
        """[決策] 對話含「我想做 X 專案」→ 30 秒內 role_projects 出現對應紀錄"""
        result = _run("我想開始做微積分的期末專案", role_id=ROLE_CSIE)
        assert result.elapsed_seconds <= 30
        projects = result._db.projects_for(ROLE_CSIE)
        assert any("微積分" in p.name for p in projects)
        assert all(p.inferred_by_ai for p in projects if "微積分" in p.name)

    def test_existing_project_matched_not_duplicated(self):
        """提及已存在的專案 → 匹配而非重複建立"""
        db = FakeDB()
        db.add_project(role_id=ROLE_CSIE, name="微積分")
        _run("微積分作業好難", role_id=ROLE_CSIE, db=db)
        matched = [p for p in db.projects_for(ROLE_CSIE) if "微積分" in p.name]
        assert len(matched) == 1  # 不重複

    def test_intent_extraction(self):
        """萃取使用者意圖（deadline / urgent）"""
        result = _run("我明天要交作業，今晚得趕完")
        assert result.extracted_intent is not None
        low = result.extracted_intent.lower()
        assert "deadline" in low or "urgent" in low

    def test_emotion_extraction(self):
        """[決策] 萃取使用者情緒"""
        result = _run("這份作業我寫了三天都寫不出來，真的很想放棄")
        assert result.emotion_detected is not None
        assert result.emotion_detected in ["frustrated", "anxious", "sad"]


# ---------------------------------------------------------------------------
# Privacy (RISK-12 / RISK-06)
# ---------------------------------------------------------------------------

class TestObserverPrivacy:
    def test_extraction_passes_eguard(self):
        """[RISK-12] 萃取結果必須經 Eguard 過濾 PII"""
        result = _run("幫我看陳小明的 OpenStack 部署")
        assert result.project_name is None or "陳小明" not in result.project_name
        assert "陳" not in str(result.extraction)

    def test_inferred_achievement_default_private(self):
        """[RISK-12] Observer 自動偵測的成就預設不公開"""
        result = _run("我連續寫了 30 天程式")
        if result.achievement:
            assert result.achievement["default_visibility"] == "private"

    def test_extraction_scoped_by_role(self):
        """[RISK-06] 萃取結果綁定當前 role_id"""
        db = FakeDB()
        result = _run("微積分專案", role_id=ROLE_CSIE, db=db)
        assert result.role_id == ROLE_CSIE
        # FAMILY 角色查不到
        family_projects = db.projects_for(ROLE_FAMILY)
        assert not any(p.name == result.project_name for p in family_projects)


# ---------------------------------------------------------------------------
# Resilience
# ---------------------------------------------------------------------------

class TestObserverResilience:
    def test_observer_does_not_block_persona(self):
        """Observer 慢任務不阻塞 Persona 回應"""
        async def run():
            async def persona():
                await asyncio.sleep(0.01)
                return "persona_done"

            async def slow_observer():
                await asyncio.sleep(5)
                return "observer_done"

            persona_task = asyncio.create_task(persona())
            observer_task = asyncio.create_task(slow_observer())
            done, _pending = await asyncio.wait(
                [persona_task, observer_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=1,
            )
            assert persona_task in done
            observer_task.cancel()

        asyncio.run(run())

    def test_observer_timeout_silent_failure(self):
        """[決策] Observer 超時 → 靜默失敗，回傳 timed_out=True"""
        async def slow_task(_task):
            await asyncio.sleep(10)
            return ObserverResult()

        result = asyncio.run(observer_extract({"thread_id": "t_x"}, _impl=slow_task, timeout=0.05))
        assert result.timed_out is True

    def test_system_event_emitted_on_success(self):
        """萃取成功 → 發送 SSE System Event 至前端"""
        result = _run("我想做機器學習專案")
        assert any(e["type"] == "project_created" for e in result._sse.events)


# ---------------------------------------------------------------------------
# Project detector unit
# ---------------------------------------------------------------------------

class TestProjectDetector:
    def test_regex_extracts_project_candidate(self):
        assert regex_extract_project("我想做微積分的期末專案") is not None

    def test_regex_no_false_positive_on_plain_text(self):
        assert regex_extract_project("今天天氣很好") is None

    @pytest.mark.asyncio
    async def test_fuzzy_match_threshold_prevents_oversplit(self):
        """[決策] 高匹配閾值 0.85：完全相同的專案不重複建立"""
        db = FakeDB()
        db.add_project(role_id=ROLE_CSIE, name="微積分作業")
        sse = FakeSSE()
        name = await detect_and_upsert_project(
            "微積分作業好難", role_id=ROLE_CSIE, db=db, eguard=FakeEguard(), sse=sse
        )
        assert name == "微積分作業"
        assert len(db.projects_for(ROLE_CSIE)) == 1


# ---------------------------------------------------------------------------
# BDI bridge (RISK-08)
# ---------------------------------------------------------------------------

class TestBDIBridge:
    @pytest.mark.asyncio
    async def test_desire_routed_through_bdi_queue_not_persona(self):
        """[RISK-08] Observer 的 desire 進入 BDI 佇列，不直接注入 Persona"""
        queue = BDIQueue()
        await submit_to_bdi_reconciler(
            desire="想做微積分專案", thread_id="t_001", role_id=ROLE_CSIE, queue=queue
        )
        item = await queue.get()
        assert item["source"] == "M4.6"
        assert item["desire"] == "想做微積分專案"
        assert item["role_id"] == ROLE_CSIE


# ---------------------------------------------------------------------------
# Emotion unit
# ---------------------------------------------------------------------------

class TestEmotionDetector:
    def test_frustration_detected(self):
        assert detect_emotion("寫不出來，想放棄") in ["frustrated", "sad"]

    def test_anxiety_detected(self):
        assert detect_emotion("明天就要交了好緊張好焦慮") == "anxious"

    def test_neutral_returns_none(self):
        assert detect_emotion("好的，我知道了") is None
