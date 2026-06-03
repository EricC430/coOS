"""
M4.4 Natural Elicitation & Draft Generator -- test suite

SPEC: docs/modules/M4_4_natural_elicitation_draft_SPEC.md §6
Research: [R10 §代理工作流 / §MindScape] [R08 §五 意圖脫鉤] [R08 §六.1 IKEA] [R08 §六.2 吉布斯]
Risk coverage: RISK-01 (draft never auto-approved), RISK-15 (no content_summary leak),
               RISK-06 (role-scoped elicitation)

Note: tests are pure-unit. The nightly draft scheduler is exercised via an injected
`today` parameter (no freezegun dependency) and a MagicMock DB store, matching the
established M4.3 test style.
"""
from __future__ import annotations

import sys
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_4_elicitation.controller import (  # noqa: E402
    CONFIDENCE_THRESHOLD,
    ElicitationController,
    ElicitationHint,
    TelemetryGap,
    TelemetrySegment,
    TelemetrySegmentReport,
)
from m4_4_elicitation.draft_scheduler import generate_draft, run_draft_cron  # noqa: E402
from m4_4_elicitation.gibbs_template import (  # noqa: E402
    build_gibbs_analysis,
    build_gibbs_description,
)
from m4_4_elicitation.ner_parser import extract_and_store, extract_duration  # noqa: E402

ROLE_CSIE = "role_csie"
USER_ID = "u_001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(payload: dict) -> SimpleNamespace:
    """Build a raw_tracking_log-like row with a payload dict."""
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        payload=payload,
        duration=payload.get("duration_minutes", 0),
    )


def _make_db(logs: list | None = None, elicited: list | None = None) -> MagicMock:
    db = MagicMock()
    db.fetch_tracking_logs = AsyncMock(return_value=logs if logs is not None else [])
    db.fetch_elicited_durations = AsyncMock(return_value=elicited if elicited is not None else [])
    db.get_user_active_roles = AsyncMock(return_value=[SimpleNamespace(id=ROLE_CSIE)])
    db.create_draft_reflection = AsyncMock(side_effect=lambda **kw: SimpleNamespace(**kw))
    db.task_slots = {}
    return db


# ---------------------------------------------------------------------------
# M4.4.1 Elicitation Controller
# ---------------------------------------------------------------------------

class TestM4_4_1_ElicitationController:
    def test_elicitation_outputs_multi_message(self):
        """[R08 §五] 套問結果為多訊息序列，模擬真人聊天節奏"""
        controller = ElicitationController()
        fragment = controller.generate_elicitation(
            context="low_confidence",
            role_id=ROLE_CSIE,
            telemetry_hint="VS Code",
            time_hint="下午",
            app_hint="VS Code",
            project_name="微積分",
        )
        assert isinstance(fragment.inject_messages, list)
        assert len(fragment.inject_messages) >= 2
        for msg in fragment.inject_messages:
            assert "請輸入耗時" not in msg

    def test_elicitation_cooldown(self):
        """每次對話最多套問 1 次，cooldown 至少 5 turn"""
        controller = ElicitationController()
        controller.record_elicitation(thread_id="t_001", turn=3)
        assert controller.can_elicit(thread_id="t_001", current_turn=5) is False
        assert controller.can_elicit(thread_id="t_001", current_turn=9) is False  # already 1 used

    def test_elicitation_cooldown_fresh_thread(self):
        """新 thread 未套問過 → 可套問"""
        controller = ElicitationController()
        assert controller.can_elicit(thread_id="t_new", current_turn=1) is True

    def test_no_elicitation_when_telemetry_confident(self):
        """背景監測自信度 >= 0.7 時不套問，避免 AI 裝傻"""
        controller = ElicitationController()
        report = TelemetrySegmentReport(
            segments=[TelemetrySegment(start="14:00", end="16:00", app_bucket="coding",
                                       confidence=0.9, duration_minutes=120)],
            gaps=[],
        )
        assert controller.should_elicit(report) is False

    def test_elicit_on_telemetry_gap(self):
        """存在未覆蓋時段 (gap) 時觸發套問"""
        controller = ElicitationController()
        report = TelemetrySegmentReport(
            segments=[],
            gaps=[TelemetryGap(start="09:00", end="12:00")],
        )
        assert controller.should_elicit(report) is True

    def test_elicit_on_low_confidence_segment(self):
        """背景監測有紀錄但自信度 < 0.7 時觸發確認性套問"""
        controller = ElicitationController()
        report = TelemetrySegmentReport(
            segments=[TelemetrySegment(start="14:00", end="15:00", app_bucket="document",
                                       confidence=0.4, duration_minutes=60)],
            gaps=[],
        )
        assert controller.should_elicit(report) is True

    def test_confidence_threshold_value(self):
        """門檻常數為 0.7（鐵律）"""
        assert CONFIDENCE_THRESHOLD == 0.7

    def test_elicitation_scoped_by_role(self):
        """[RISK-06] 套問只針對當前角色的專案"""
        controller = ElicitationController()
        fragment = controller.generate_elicitation(
            context="telemetry_gap",
            role_id=ROLE_CSIE,
        )
        assert fragment.target_role_id == ROLE_CSIE

    def test_from_observer_hint_scopes_role_and_project(self):
        """[M4.6->M4.4] Observer 新專案提示轉套問，沿用 role_id 與 project_name"""
        controller = ElicitationController()
        hint = ElicitationHint(
            context="new_project_detected", project_name="微積分期末專案", role_id=ROLE_CSIE
        )
        fragment = controller.from_observer_hint(hint)
        assert fragment.target_role_id == ROLE_CSIE
        assert any("微積分期末專案" in m for m in fragment.inject_messages)


# ---------------------------------------------------------------------------
# M4.4.2 NER Parser
# ---------------------------------------------------------------------------

class TestM4_4_2_NERParser:
    def test_parse_duration_from_chat(self):
        """從使用者回覆抽取時間跨度"""
        result = extract_duration("大概花了三個半小時吧")
        assert result is not None
        assert result.minutes == 210

    def test_parse_duration_various_formats(self):
        assert extract_duration("30分鐘").minutes == 30
        assert extract_duration("about 2 hours").minutes == 120
        assert extract_duration("一個下午").minutes == 240  # 預設 4h

    def test_parse_half_hour(self):
        assert extract_duration("半小時").minutes == 30

    def test_no_duration_returns_none(self):
        """無法辨識時間 → 回傳 None，不猜測"""
        assert extract_duration("我覺得還好") is None

    @pytest.mark.asyncio
    async def test_parsed_result_written_to_task_slot(self):
        """解析結果寫入任務暫存槽供 M4.4.3 使用"""
        db = _make_db()
        await extract_and_store(
            db, thread_id="t_001", user_msg="花了兩小時",
            role_id=ROLE_CSIE, project="微積分",
        )
        slot = db.task_slots["t_001"]
        assert slot["duration_minutes"] == 120
        assert slot["project"] == "微積分"


# ---------------------------------------------------------------------------
# M4.4.3 Draft Scheduler
# ---------------------------------------------------------------------------

class TestM4_4_3_DraftScheduler:
    @pytest.mark.asyncio
    async def test_daily_draft_generated(self):
        """每日排程自動產出前一日草稿（前一日 = today - 1）"""
        db = _make_db(logs=[_log({"app_bucket": "coding", "duration_minutes": 90})])
        drafts = await run_draft_cron(USER_ID, db=db, today=date(2026, 6, 3))
        assert len(drafts) >= 1
        assert all(d.reflection_date == date(2026, 6, 2) for d in drafts)

    @pytest.mark.asyncio
    async def test_draft_is_always_draft(self):
        """[RISK-01] 草稿必須是 is_draft=true, is_reviewed=false, 主觀欄位留空"""
        db = _make_db(logs=[_log({"app_bucket": "coding", "duration_minutes": 90})])
        draft = await generate_draft(USER_ID, ROLE_CSIE, date(2026, 6, 2), db=db)
        assert draft.is_draft is True
        assert draft.is_reviewed is False
        assert draft.user_feeling is None
        assert draft.user_action_plan is None

    @pytest.mark.asyncio
    async def test_draft_contains_gibbs_structure(self):
        """[R08 §六.2] 草稿遵循吉布斯反思結構"""
        db = _make_db(logs=[
            _log({"app_bucket": "coding", "duration_minutes": 90}),
            _log({"app_bucket": "document", "duration_minutes": 40}),
        ])
        draft = await generate_draft(USER_ID, ROLE_CSIE, date(2026, 6, 2), db=db)
        assert draft.ai_description is not None
        assert draft.ai_analysis is not None
        assert len(draft.ai_description) >= 20

    @pytest.mark.asyncio
    async def test_draft_uses_generalized_content(self):
        """[RISK-15] ai_description 不含 content_summary 原文"""
        db = _make_db(logs=[
            _log({"app_bucket": "document", "duration_minutes": 90,
                  "content_summary": "編輯畢業論文第五章結論"}),
        ])
        draft = await generate_draft(USER_ID, ROLE_CSIE, date(2026, 6, 2), db=db)
        assert "畢業論文" not in draft.ai_description
        assert "第五章" not in draft.ai_description

    @pytest.mark.asyncio
    async def test_draft_links_source_log_ids(self):
        """草稿必須記錄 source_log_ids 供反溯因驗證"""
        log = _log({"app_bucket": "coding", "duration_minutes": 90})
        db = _make_db(logs=[log])
        draft = await generate_draft(USER_ID, ROLE_CSIE, date(2026, 6, 2), db=db)
        assert draft.source_log_ids is not None
        assert len(draft.source_log_ids) >= 1

    @pytest.mark.asyncio
    async def test_no_activity_no_draft(self):
        """無任何活動記錄的日期不產出草稿"""
        db = _make_db(logs=[])
        drafts = await run_draft_cron(USER_ID, db=db, today=date(2026, 6, 3))
        assert len(drafts) == 0


# ---------------------------------------------------------------------------
# Gibbs template unit
# ---------------------------------------------------------------------------

class TestGibbsTemplate:
    def test_description_uses_only_generalized_metrics(self):
        """[RISK-15] description 僅使用 app_bucket / duration，不洩漏 content_summary"""
        logs = [_log({"app_bucket": "coding", "duration_minutes": 90,
                      "content_summary": "畢業論文第五章"})]
        desc = build_gibbs_description(logs, [])
        assert "畢業論文" not in desc
        assert "coding" in desc

    def test_analysis_defers_subjective_to_user(self):
        """[R08 §五] analysis 不填主觀感受，留給使用者"""
        logs = [_log({"app_bucket": "coding", "duration_minutes": 90})]
        analysis = build_gibbs_analysis(logs, [])
        assert "請您" in analysis or "主觀" in analysis
