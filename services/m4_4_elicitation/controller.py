"""
M4.4.1 -- 對話套問控制器 (Elicitation Controller)

實作 SPEC: docs/modules/M4_4_natural_elicitation_draft_SPEC.md §7.1
研究依據: [R08 §五 意圖脫鉤] 套問由 Persona 自然帶出，AI 只填客觀數據

設計原則 (SPEC §7.1):
- M4.4 不自行做 domain 匹配；語意分類與專家分配由 M4.6 Observer 統一處理。
- 自信度門檻 CONFIDENCE_THRESHOLD=0.7：高於此值的時段不套問（避免 AI 裝傻）。
- 套問不限於時間：也確認未覆蓋時段活動與低自信度時段內容。
- 頻率限制：每個 thread 最多套問 1 次，cooldown 5 turn。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Schema (consumed from M4.6 Observer's TelemetrySegmentReport)
# ---------------------------------------------------------------------------


@dataclass
class TelemetrySegment:
    """由 M4.6 Observer 回掃後產出的單一時段報告。"""

    start: str  # "14:00"
    end: str  # "16:00"
    app_bucket: str  # "coding" / "document" / "browser" / "unknown"
    confidence: float  # 0.0~1.0，語意分類自信度
    duration_minutes: int
    project_name: str | None = None


@dataclass
class TelemetryGap:
    """完全沒有遙測數據的空白時段（使用者離線/未使用 coOS）。"""

    start: str
    end: str
    confidence: float = 0.0  # 永遠為 0


@dataclass
class TelemetrySegmentReport:
    """M4.6 Observer 進入聊天室時回掃近期遙測產出的報告。"""

    segments: list[TelemetrySegment] = field(default_factory=list)
    gaps: list[TelemetryGap] = field(default_factory=list)


@dataclass
class ElicitationHint:
    """
    M4.6 Observer 偵測到新專案後送來的套問提示（SPEC §3 Outputs / M4.6 §3）。
    M4.4 據此決定是否就該專案發起耗時套問。
    """

    context: str  # e.g. "new_project_detected"
    project_name: str
    role_id: str


@dataclass
class ElicitationPromptFragment:
    """套問結果：多訊息序列（模擬真人分段發送）。"""

    inject_messages: list[str]  # 2~4 個獨立訊息氣泡
    context: str  # "telemetry_gap" / "low_confidence" / "duration_confirm" / ...
    target_role_id: str
    cooldown_turns: int = 5


# 套問模板：每個 key 對應一個多訊息序列。
# [R08 §五] 措辭刻意非機器式，由 Persona 語氣自然帶出。
ELICITATION_TEMPLATES: dict[str, list[str]] = {
    "telemetry_observed": [
        "我從後台紀錄看到你{time_hint}有在{activity_hint}耶",
        "今天進度怎麼樣",
        "有做到預計的目標嗎？",
    ],
    "telemetry_gap": [
        "我看你{time_hint}好像沒有在電腦前",
        "有做什麼跟{project_name}相關的事嗎？",
    ],
    "low_confidence": [
        "後台有記錄到你{time_hint}開了{app_hint}一陣子",
        "是在做{project_name}的東西嗎？",
    ],
    "general_duration": [
        "對了，{project_name}這個大概花了你多久？",
    ],
}

CONFIDENCE_THRESHOLD = 0.7  # 自信度門檻（鐵律，見 SPEC §8 反模式）


class ElicitationController:
    """每個 thread 最多套問 1 次，cooldown 5 turn。"""

    MAX_PER_THREAD = 1
    COOLDOWN_TURNS = 5

    def __init__(self) -> None:
        self._history: dict[str, list[int]] = {}  # thread_id -> [turn_numbers]

    # ------------------------------------------------------------------
    # 頻率限制
    # ------------------------------------------------------------------

    def record_elicitation(self, thread_id: str, turn: int) -> None:
        """記錄一次套問發生於某 turn。"""
        self._history.setdefault(thread_id, []).append(turn)

    def can_elicit(self, thread_id: str, current_turn: int) -> bool:
        """頻率限制檢查：上限 1 次 / thread，且距離上次至少 COOLDOWN_TURNS。"""
        history = self._history.get(thread_id, [])
        if len(history) >= self.MAX_PER_THREAD:
            return False
        if history and (current_turn - history[-1]) < self.COOLDOWN_TURNS:
            return False
        return True

    # ------------------------------------------------------------------
    # 觸發判斷
    # ------------------------------------------------------------------

    def should_elicit(self, report: TelemetrySegmentReport) -> bool:
        """
        [自信度門檻] 判斷是否需要套問：
        - 存在 gap (完全未覆蓋時段) -> True
        - 存在 confidence < CONFIDENCE_THRESHOLD 的時段 -> True
        - 所有時段 confidence >= CONFIDENCE_THRESHOLD -> False (避免裝傻)
        """
        if report.gaps:
            return True
        return any(seg.confidence < CONFIDENCE_THRESHOLD for seg in report.segments)

    # ------------------------------------------------------------------
    # 套問生成
    # ------------------------------------------------------------------

    def generate_elicitation(
        self,
        context: str,
        role_id: str,
        persona_tone: str = "empathetic",
        telemetry_hint: str = "",
        time_hint: str = "",
        app_hint: str = "",
        project_name: str = "",
    ) -> ElicitationPromptFragment:
        """
        生成多訊息序列的套問 Fragment。
        每個訊息由前端以獨立氣泡渲染，中間插入 300~1500ms 隨機延遲。
        [RISK-06] target_role_id 嚴格綁定當前角色。
        """
        templates = ELICITATION_TEMPLATES.get(context, ELICITATION_TEMPLATES["general_duration"])
        # 缺值欄位代換為通用詞，避免出現空白佔位符。
        messages = [
            t.format(
                time_hint=time_hint or "稍早",
                activity_hint=telemetry_hint or "做事",
                app_hint=app_hint or "程式",
                project_name=project_name or "這個專案",
            )
            for t in templates
        ]
        return ElicitationPromptFragment(
            inject_messages=messages,
            context=context,
            target_role_id=role_id,
        )

    def from_observer_hint(self, hint: ElicitationHint) -> ElicitationPromptFragment:
        """
        [M4.6 -> M4.4 整合] 將 Observer 的新專案偵測提示轉為耗時套問。
        [RISK-06] 沿用 hint 的 role_id，套問嚴格綁定當前角色。
        """
        return self.generate_elicitation(
            context="general_duration",
            role_id=hint.role_id,
            project_name=hint.project_name,
        )
