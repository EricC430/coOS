"""
M4.6 v1.2 extractors -- promise / goal / intention test suite

SPEC: docs/modules/M4_6_observer_agent_SPEC.md §7.4-7.6
Risk coverage: RISK-12 (promise text + goal title pass Eguard before persistence)

These exercise the LLM-backed extractors with an injected fake Gemma so the
JSON contract and the Eguard PII gate are tested deterministically.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_6_observer.goal_detector import detect_goal_establishment  # noqa: E402
from m4_6_observer.intention_extractor import extract_session_intention  # noqa: E402
from m4_6_observer.promise_extractor import extract_promises  # noqa: E402

ROLE_CSIE = "role_csie"
PERSONA = "persona_001"


class FakeEguard:
    def filter_pii(self, text: str) -> str:
        return text.replace("陳小明", "[REDACTED]").replace("陳", "[REDACTED]")


class FakeGemma:
    def __init__(self, json_value=None, text_value=""):
        self._json = json_value
        self._text = text_value

    async def generate_json(self, prompt: str):
        return self._json

    async def generate_text(self, prompt: str):
        return self._text


@dataclass
class FakeDB:
    promises: list = field(default_factory=list)
    goals: list = field(default_factory=list)
    transcripts: dict = field(default_factory=dict)
    session_intentions: dict = field(default_factory=dict)

    async def insert_promise(self, **kw):
        self.promises.append(kw)

    async def insert_goal(self, **kw):
        self.goals.append(kw)

    async def fetch_thread_transcripts(self, thread_id):
        return self.transcripts.get(thread_id, [])

    async def set_session_intention(self, thread_id, intention):
        self.session_intentions[thread_id] = intention


class FakeSSE:
    def __init__(self):
        self.events = []

    async def emit(self, event_type, data):
        self.events.append({"type": event_type, "data": data})


# ---------------------------------------------------------------------------
# Promise extraction (RISK-12)
# ---------------------------------------------------------------------------

class TestPromiseExtraction:
    @pytest.mark.asyncio
    async def test_promise_written_and_pii_filtered(self):
        """[RISK-12] 承諾原文經 Eguard 泛化後才寫入 promises 表"""
        gemma = FakeGemma(json_value=[{"text": "幫陳小明做報告", "deadline": None}])
        db = FakeDB()
        sse = FakeSSE()
        written = await extract_promises(
            "我答應幫陳小明做報告", thread_id="t1", role_id=ROLE_CSIE, persona_id=PERSONA,
            gemma=gemma, eguard=FakeEguard(), db=db, sse=sse,
        )
        assert len(db.promises) == 1
        assert "陳小明" not in db.promises[0]["text"]
        assert any(e["type"] == "PROMISE_RECORDED" for e in sse.events)
        assert written

    @pytest.mark.asyncio
    async def test_no_promise_returns_empty(self):
        gemma = FakeGemma(json_value=[])
        db = FakeDB()
        written = await extract_promises(
            "今天天氣不錯", thread_id="t1", role_id=ROLE_CSIE, persona_id=PERSONA,
            gemma=gemma, eguard=FakeEguard(), db=db, sse=FakeSSE(),
        )
        assert written == []
        assert db.promises == []

    @pytest.mark.asyncio
    async def test_malformed_llm_output_silent(self):
        """LLM 回傳格式錯誤 -> 靜默忽略，不拋例外"""
        gemma = FakeGemma(json_value="not-json{")
        written = await extract_promises(
            "x", thread_id="t1", role_id=ROLE_CSIE, persona_id=PERSONA,
            gemma=gemma, eguard=FakeEguard(), db=FakeDB(), sse=FakeSSE(),
        )
        assert written == []


# ---------------------------------------------------------------------------
# Goal detection (RISK-12 + dedup)
# ---------------------------------------------------------------------------

class TestGoalDetection:
    @pytest.mark.asyncio
    async def test_new_goal_written_and_confirmed(self):
        gemma = FakeGemma(json_value={"title": "通過微積分期末考", "description": "目標細節"})
        db = FakeDB()
        sse = FakeSSE()
        goal = await detect_goal_establishment(
            "我希望能通過微積分期末考", assistant_msg="所以你的目標是...",
            thread_id="t1", role_id=ROLE_CSIE, persona_id=PERSONA, existing_goals=[],
            gemma=gemma, eguard=FakeEguard(), db=db, sse=sse,
        )
        assert goal is not None
        assert len(db.goals) == 1
        assert any(e["type"] == "GOAL_CONFIRMED" for e in sse.events)

    @pytest.mark.asyncio
    async def test_duplicate_goal_not_rewritten(self):
        gemma = FakeGemma(json_value={"title": "通過微積分期末考", "description": ""})
        db = FakeDB()
        goal = await detect_goal_establishment(
            "我希望能通過微積分期末考", assistant_msg="...",
            thread_id="t1", role_id=ROLE_CSIE, persona_id=PERSONA,
            existing_goals=[{"title": "通過微積分期末考"}],
            gemma=gemma, eguard=FakeEguard(), db=db, sse=FakeSSE(),
        )
        assert goal is None
        assert db.goals == []

    @pytest.mark.asyncio
    async def test_no_goal_returns_none(self):
        gemma = FakeGemma(json_value=None)
        goal = await detect_goal_establishment(
            "嗯嗯", assistant_msg="...", thread_id="t1", role_id=ROLE_CSIE,
            persona_id=PERSONA, existing_goals=[],
            gemma=gemma, eguard=FakeEguard(), db=FakeDB(), sse=FakeSSE(),
        )
        assert goal is None


# ---------------------------------------------------------------------------
# Session intention
# ---------------------------------------------------------------------------

class TestSessionIntention:
    @pytest.mark.asyncio
    async def test_intention_extracted_and_stored(self):
        gemma = FakeGemma(text_value="想搞懂微積分的極限概念")
        db = FakeDB()
        db.transcripts["t1"] = [
            {"role": "user", "content": "極限是什麼"},
            {"role": "assistant", "content": "極限是..."},
        ]
        intention = await extract_session_intention(
            thread_id="t1", role_id=ROLE_CSIE, persona_id=PERSONA, gemma=gemma, db=db
        )
        assert intention == "想搞懂微積分的極限概念"
        assert db.session_intentions["t1"] == intention

    @pytest.mark.asyncio
    async def test_empty_thread_returns_none(self):
        gemma = FakeGemma(text_value="")
        db = FakeDB()
        intention = await extract_session_intention(
            thread_id="t_empty", role_id=ROLE_CSIE, persona_id=PERSONA, gemma=gemma, db=db
        )
        assert intention is None
