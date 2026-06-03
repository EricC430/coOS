# M4.4 — 自然套問與草稿生成器 (Natural Elicitation & Draft Generator)

**標籤**:`[MVP]`
**版本**:`1.0` / `draft`
**最後更新**:2026-06-03

## 1. Purpose (目的)

透過兩階段管線產出每日反思草稿：白天在 Persona 對話中，當背景監測自信度不足或存在未覆蓋時段時，自然套問耗時與活動資訊並解析結構化數據；深夜排程自動拉取 `raw_tracking_logs` 拼裝吉布斯反思循環草稿，寫入 `daily_reflections` 且標記 `is_draft = true`。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R10 | §代理工作流狀態機 | M4.4.3 深夜 Cron 排程的狀態機設計 |
| R10 | §MindScape 反思鷹架 | M4.4.3 吉布斯反思循環 (描述→分析→感受→行動) 的結構化模板 |
| R08 | §五 意圖脫鉤 | M4.4.1/M4.4.3 AI 只填客觀數據，主觀感受留給使用者 (M3.3.3) |
| R08 | §六.1 IKEA 效應 | M4.4 產出的草稿**必須**標記 `is_draft = true`，絕不自動核准 |
| R08 | §六.2 吉布斯循環 | M4.4.3 草稿結構源自吉布斯六階段反思模型 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.2 Persona 對話流 | `ChatMessage` | `{"thread_id": "t_001", "content": "這份微積分作業大概花了我三小時", "role": "user"}` |
| M4.6 Observer 背景回掃結果 | `TelemetrySegmentReport` | `{"segments": [...], "gaps": [{"start": "09:00", "end": "12:00", "confidence": 0.0}]}` |
| M6.1 `raw_tracking_logs` | DB Rows | 前一日所有 `module='M1.*'` 的遙測事件 |
| M6.1 `chat_transcripts` | DB Rows | 前一日所有對話記錄 (含已套問到的耗時) |
| M1.5 微 Nudges 回覆 (若有) | `NudgeResponse` | `{"target_alignment": true, "role_id": "role_csie"}` |
| M4.3 `RoleContext` | 角色上下文 | 決定草稿歸屬角色、專案範圍 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.2 Persona Prompt 注入 | `ElicitationPromptFragment` | `{"inject_messages": ["...", "..."], "context": "telemetry_gap"}` |
| M6.1 `chat_transcripts` (套問結果) | 標記 `elicitation_tag` | 標記哪些對話 turn 是套問結果 |
| M6.4 `daily_reflections` | `DraftReflection` | `{is_draft: true, ai_description: "...", ai_analysis: "...", source_log_ids: [...]}` |
| M0.4 結構化日誌 | `LogEvent` | 記錄套問觸發、解析結果、草稿生成事件 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.1** (Agent 路由)：套問注入透過 LangGraph 節點觸發
- **M4.2** (Persona 狀態機)：套問問句由 Persona 的語氣包裝，經多訊息分割器輸出，不可破壞人設
- **M4.3** (角色隔離)：草稿嚴格歸屬當前 `role_id`
- **M4.6** (Observer 背景萃取)：提供 `TelemetrySegmentReport`（含語意分類與自信度），M4.4 **不自行做 domain keyword 匹配**
- **M6.1** (SQLite)：讀取 `raw_tracking_logs` 與 `chat_transcripts`
- **M6.4** (daily_reflections 表)：寫入草稿記錄

### 下游 (誰依賴我)

- **M3.3.3** (草稿核准彈窗)：讀取 `is_draft = true` 的記錄供使用者審閱
- **M4.5** (XP 自動結算)：等待 `is_reviewed = true` 後才結算 (RISK-01)
- **M3.8** (Wrapped 彈窗)：基於已核准的反思資料做統計

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-01** | 草稿自動產出後若被 M4.5 直接結算 XP → IKEA 效應失效 | M4.4 產出的記錄**永遠** `is_draft=true, is_reviewed=false`；M4.5 必須檢查 `is_reviewed=true` 才發放 |
| **RISK-15** | M4.4.3 草稿引用 `content_summary` (M1.1 Opt-in) 原文後同步至雲端 → 側通道洩漏 | 草稿 `ai_description` 只可使用 `app_bucket`、`duration_minutes` 等泛化指標；若需引用 `content_summary`，必須先經 M2.3 Eguard 泛化 |
| (無直接 RISK-xx) | 套問頻率過高 → 使用者覺得被審問 | 每次對話最多套問 1 次；cooldown 至少 5 個 turn |
| (無直接 RISK-xx) | 背景監測已有高自信度數據時仍套問 → 使用者覺得 AI 裝傻 | 套問前必須檢查 `TelemetrySegmentReport.confidence`；自信度 ≥ 0.7 的時段不觸發套問 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m4_4/test_natural_elicitation_draft.py

import pytest
from datetime import date, time

class TestM4_4_1_ElicitationController:
    def test_elicitation_outputs_multi_message(self):
        """套問結果為多訊息序列，模擬真人聊天節奏"""
        fragment = elicitation_controller.generate_elicitation(
            context="telemetry_gap",
            telemetry_hint="下午有在 VS Code 寫程式",
            persona_tone="empathetic"
        )
        assert isinstance(fragment.inject_messages, list)
        assert len(fragment.inject_messages) >= 2
        # 不可出現機器式語句
        for msg in fragment.inject_messages:
            assert "請輸入耗時" not in msg

    def test_elicitation_cooldown(self):
        """每次對話最多套問 1 次，cooldown 至少 5 turn"""
        controller = ElicitationController()
        controller.record_elicitation(thread_id="t_001", turn=3)
        assert controller.can_elicit(thread_id="t_001", current_turn=5) is False
        assert controller.can_elicit(thread_id="t_001", current_turn=9) is True

    def test_no_elicitation_when_telemetry_confident(self):
        """背景監測自信度 >= 0.7 時不套問，避免 AI 裝傻"""
        report = TelemetrySegmentReport(
            segments=[{"start": "14:00", "end": "16:00", "app_bucket": "coding",
                       "confidence": 0.9, "duration_minutes": 120}],
            gaps=[]
        )
        assert controller.should_elicit(report) is False

    def test_elicit_on_telemetry_gap(self):
        """存在未覆蓋時段 (gap) 時觸發套問"""
        report = TelemetrySegmentReport(
            segments=[],
            gaps=[{"start": "09:00", "end": "12:00", "confidence": 0.0}]
        )
        assert controller.should_elicit(report) is True

    def test_elicit_on_low_confidence_segment(self):
        """背景監測有紀錄但自信度 < 0.7 時觸發確認性套問"""
        report = TelemetrySegmentReport(
            segments=[{"start": "14:00", "end": "15:00", "app_bucket": "document",
                       "confidence": 0.4, "duration_minutes": 60}],
            gaps=[]
        )
        assert controller.should_elicit(report) is True

    def test_elicitation_scoped_by_role(self):
        """[RISK-06] 套問只針對當前角色的專案"""
        fragment = elicitation_controller.generate_elicitation(
            context="telemetry_gap",
            role_id="role_csie"
        )
        assert fragment.target_role_id == "role_csie"

class TestM4_4_2_NERParser:
    def test_parse_duration_from_chat(self):
        """從使用者回覆抽取時間跨度"""
        result = ner_parser.extract_duration("大概花了三個半小時吧")
        assert result.minutes == 210

    def test_parse_duration_various_formats(self):
        """支援多種時間表達格式"""
        assert ner_parser.extract_duration("30分鐘").minutes == 30
        assert ner_parser.extract_duration("about 2 hours").minutes == 120
        assert ner_parser.extract_duration("一個下午").minutes == 240  # 預設 4h

    def test_no_duration_returns_none(self):
        """無法辨識時間 → 回傳 None，不猜測"""
        result = ner_parser.extract_duration("我覺得還好")
        assert result is None

    def test_parsed_result_written_to_task_slot(self, db):
        """解析結果寫入任務暫存槽供 M4.4.3 使用"""
        ner_parser.extract_and_store(
            thread_id="t_001", user_msg="花了兩小時",
            role_id="role_csie", project="微積分"
        )
        slot = db.query_task_slot(thread_id="t_001")
        assert slot.duration_minutes == 120
        assert slot.project == "微積分"

class TestM4_4_3_DraftScheduler:
    def test_daily_draft_generated_at_0200(self):
        """每日 02:00 自動產出前一日草稿"""
        with freeze_time("2026-06-03 02:00:00"):
            drafts = run_draft_cron(user_id="u_001")
        assert len(drafts) >= 1
        assert all(d.reflection_date == date(2026, 6, 2) for d in drafts)

    def test_draft_is_always_draft(self):
        """[RISK-01] 草稿必須是 is_draft=true, is_reviewed=false"""
        draft = generate_draft(user_id="u_001", role_id="role_csie")
        assert draft.is_draft is True
        assert draft.is_reviewed is False
        assert draft.user_feeling is None
        assert draft.user_action_plan is None

    def test_draft_contains_gibbs_structure(self):
        """[R08 §六.2] 草稿遵循吉布斯反思結構"""
        draft = generate_draft(user_id="u_001", role_id="role_csie")
        assert draft.ai_description is not None  # 客觀描述
        assert draft.ai_analysis is not None      # 初步分析
        assert len(draft.ai_description) >= 20

    def test_draft_uses_generalized_content(self):
        """[RISK-15] ai_description 不含 content_summary 原文"""
        draft = generate_draft(
            user_id="u_001", role_id="role_csie",
            log_with_content_summary="編輯畢業論文第五章結論"
        )
        assert "畢業論文" not in draft.ai_description
        assert "第五章" not in draft.ai_description

    def test_draft_links_source_log_ids(self):
        """草稿必須記錄 source_log_ids 供反溯因驗證"""
        draft = generate_draft(user_id="u_001", role_id="role_csie")
        assert draft.source_log_ids is not None
        assert len(draft.source_log_ids) >= 1

    def test_no_activity_no_draft(self):
        """無任何活動記錄的日期不產出草稿"""
        with empty_tracking_logs():
            drafts = run_draft_cron(user_id="u_001")
        assert len(drafts) == 0
```

## 7. Implementation Notes

### 7.1 對話套問控制器 (M4.4.1)

> [!IMPORTANT]
> **設計原則：M4.4 不自行做 domain 匹配**。背景遙測的語意分類與專家分配由 M4.6 Observer 統一處理（語意級別，非關鍵字字串比對）。M4.4 僅在收到 Observer 的 `TelemetrySegmentReport` 後，依據自信度門檻決定「是否需要套問」以及「套問什麼」。

> [!IMPORTANT]
> **設計原則：自信度門檻機制**。當 `TelemetrySegmentReport` 中某時段的 `confidence >= 0.7` 時，背景監測已有足夠可靠的數據，M4.4 **不發起套問**（避免 AI 裝傻）。僅當 `confidence < 0.7`（低自信度時段）或存在完全空白的 `gap`（未監測到的時段，如使用者離開筆電或未使用 coOS）時，才觸發套問。

> [!IMPORTANT]
> **設計原則：套問不限於時間**。套問內容不僅僅是「花了多久？」，還包含對未覆蓋時段的活動確認（如「你上午好像沒在線上，有做什麼跟專案相關的事嗎？」）以及對低自信度時段的內容確認（如「你下午在 Word 裡忙了好一陣子，是在寫報告嗎？」）。

```python
# services/m4_4_elicitation/controller.py
# [R08 §五 意圖脫鉤] 套問由 Persona 自然帶出

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TelemetrySegment:
    """由 M4.6 Observer 回掃後產出的單一時段報告"""
    start: str              # "14:00"
    end: str                # "16:00"
    app_bucket: str         # "coding" / "document" / "browser" / "unknown"
    confidence: float       # 0.0~1.0，語意分類自信度
    duration_minutes: int
    project_name: Optional[str] = None

@dataclass
class TelemetryGap:
    """完全沒有遙測數據的空白時段（使用者離線/未使用 coOS）"""
    start: str
    end: str
    confidence: float = 0.0  # 永遠為 0

@dataclass
class TelemetrySegmentReport:
    """M4.6 Observer 進入聊天室時回掃近期遙測產出的報告"""
    segments: list[TelemetrySegment] = field(default_factory=list)
    gaps: list[TelemetryGap] = field(default_factory=list)

@dataclass
class ElicitationPromptFragment:
    """套問結果：多訊息序列（模擬真人分段發送）"""
    inject_messages: list[str]    # 2~4 個獨立訊息氣泡
    context: str                  # "telemetry_gap" / "low_confidence" / "duration_confirm"
    target_role_id: str
    cooldown_turns: int = 5

# 套問模板：每個 key 對應一個多訊息序列
ELICITATION_TEMPLATES = {
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

CONFIDENCE_THRESHOLD = 0.7  # 自信度門檻

class ElicitationController:
    """每個 thread 最多套問 1 次，cooldown 5 turn"""
    MAX_PER_THREAD = 1
    COOLDOWN_TURNS = 5

    def __init__(self):
        self._history: dict[str, list[int]] = {}  # thread_id → [turn_numbers]

    def can_elicit(self, thread_id: str, current_turn: int) -> bool:
        """頻率限制檢查"""
        history = self._history.get(thread_id, [])
        if len(history) >= self.MAX_PER_THREAD:
            return False
        if history and (current_turn - history[-1]) < self.COOLDOWN_TURNS:
            return False
        return True

    def should_elicit(self, report: TelemetrySegmentReport) -> bool:
        """
        [自信度門檻] 判斷是否需要套問：
        - 存在 gap (完全未覆蓋時段) → True
        - 存在 confidence < CONFIDENCE_THRESHOLD 的時段 → True
        - 所有時段 confidence >= CONFIDENCE_THRESHOLD → False (不套問，避免裝傻)
        """
        if report.gaps:
            return True
        return any(seg.confidence < CONFIDENCE_THRESHOLD for seg in report.segments)

    def generate_elicitation(
        self, context: str, role_id: str,
        persona_tone: str = "empathetic",
        telemetry_hint: str = "",
        time_hint: str = "",
        app_hint: str = "",
        project_name: str = "",
    ) -> ElicitationPromptFragment:
        """
        生成多訊息序列的套問 Fragment。
        每個訊息由前端以獨立氣泡渲染，中間插入 300~1500ms 隨機延遲。
        """
        templates = ELICITATION_TEMPLATES.get(context, ELICITATION_TEMPLATES["general_duration"])
        messages = [
            t.format(
                time_hint=time_hint,
                activity_hint=telemetry_hint,
                app_hint=app_hint,
                project_name=project_name,
            )
            for t in templates
        ]
        return ElicitationPromptFragment(
            inject_messages=messages,
            context=context,
            target_role_id=role_id,
        )
```

### 7.2 NER + Regex 時間解析器 (M4.4.2)

```python
# services/m4_4_elicitation/ner_parser.py
# [R10 §代理工作流] 從聊天抽取結構化時間

import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class DurationResult:
    minutes: int
    raw_text: str
    confidence: float  # 0.0~1.0

# 中英文時間模式
DURATION_PATTERNS = [
    (r"(\d+)\s*(?:小時|hours?|hrs?)", lambda m: int(m.group(1)) * 60),
    (r"(\d+)\s*(?:分鐘|minutes?|mins?)", lambda m: int(m.group(1))),
    (r"半\s*(?:小時|hour)", lambda _: 30),
    (r"(\d+)\s*個半\s*小時", lambda m: int(m.group(1)) * 90),
    (r"一個\s*(?:下午|上午|早上)", lambda _: 240),
]

def extract_duration(text: str) -> Optional[DurationResult]:
    total = 0
    matched = False
    for pattern, calc in DURATION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            total += calc(match)
            matched = True
    if not matched:
        return None
    return DurationResult(minutes=total, raw_text=text, confidence=0.8)
```

### 7.3 深夜草稿排程器 (M4.4.3)

```python
# services/m4_4_elicitation/draft_scheduler.py
# [R10 §MindScape + R08 §六.2 吉布斯循環]

from datetime import date, timedelta

async def run_draft_cron(user_id: str):
    """
    每日 02:00 排程。
    [RISK-01] 產出的草稿永遠 is_draft=true。
    [RISK-15] ai_description 不含 content_summary 原文。
    """
    yesterday = date.today() - timedelta(days=1)
    roles = await get_user_active_roles(user_id)
    drafts = []

    for role in roles:
        # 1. 拉取前一日遙測
        logs = await fetch_tracking_logs(user_id, role.id, yesterday)
        if not logs:
            continue  # 無活動 → 不生成草稿

        # 2. 拉取套問結果 (M4.4.1+M4.4.2 白天收集的)
        elicited = await fetch_elicited_durations(user_id, role.id, yesterday)

        # 3. 拼裝吉布斯描述
        ai_description = build_gibbs_description(logs, elicited)
        ai_analysis = build_gibbs_analysis(logs, elicited)

        # 4. [RISK-15] 泛化 content_summary
        ai_description = await eguard_generalize(ai_description)

        # 5. 寫入 daily_reflections [RISK-01]
        draft = await create_draft_reflection(
            user_id=user_id,
            role_id=role.id,
            reflection_date=yesterday,
            ai_description=ai_description,
            ai_analysis=ai_analysis,
            source_log_ids=[log.id for log in logs],
            activity_minutes=sum(log.duration for log in logs),
            # [RISK-01] 以下欄位永遠為預設值
            is_draft=True,
            is_reviewed=False,
            user_feeling=None,
            user_action_plan=None,
        )
        drafts.append(draft)

    return drafts
```

### 7.4 吉布斯反思結構模板

```python
# services/m4_4_elicitation/gibbs_template.py
# [R08 §六.2 + R10 §MindScape]

def build_gibbs_description(logs, elicited) -> str:
    """
    吉布斯階段 1: 客觀描述 (AI 填寫)
    只用泛化指標: app_bucket, duration, wpm_avg
    [RISK-15] 禁止使用 content_summary, window_title
    """
    segments = []
    for log in logs:
        bucket = log.payload.get("app_bucket", "unknown")
        duration = log.payload.get("duration_minutes", 0)
        segments.append(f"在「{bucket}」類型活動上花費約 {duration} 分鐘")

    # 加入套問取得的自報耗時
    for e in elicited:
        segments.append(f"自述「{e.project}」花費約 {e.minutes} 分鐘")

    return "；".join(segments) + "。"

def build_gibbs_analysis(logs, elicited) -> str:
    """
    吉布斯階段 2: 初步分析 (AI 填寫)
    [R08 §五] 不填主觀感受，留給使用者
    """
    total_mins = sum(l.payload.get("duration_minutes", 0) for l in logs)
    return f"全日活躍約 {total_mins} 分鐘。" + "（主觀感受與行動計畫請您親自填寫）"
```

### 7.5 異常處理

- **iPad 不可達 (M2.2 離線)** → 草稿仍可產出，只是缺少 `content_summary` 泛化，降級為純 `app_bucket` 描述
- **`daily_reflections` 已存在同天記錄** → `UNIQUE` 約束拒絕，更新既有草稿而非新建
- **排程器超時 (>60s)** → 中止當前角色的草稿生成，記錄 `draft_timeout` 事件，下次排程重試
- **NER 解析失敗** → 回傳 `None`，不猜測時間；草稿的 `activity_minutes` 僅依賴遙測數據
- **無任何遙測記錄的日期** → 不產出草稿，避免空洞反思

## 8. Anti-patterns (反模式)

❌ **不要自動將草稿的 `is_reviewed` 設為 `true`**
   理由：CLAUDE.md 鐵律第 1 條；RISK-01；R08 IKEA 效應。草稿永遠是草稿，直到使用者在 M3.3.3 手動核准。

❌ **不要在 `ai_description` 中嵌入 `content_summary`、`window_title` 或 `content_raw` 原文**
   理由：RISK-15。`daily_reflections` 存在雲端 PostgreSQL，嵌入 L1 明文會造成側通道洩漏。必須經 M2.3 Eguard 泛化。

❌ **不要讓套問頻率超過每個 thread 1 次**
   理由：過度套問會讓使用者覺得被審問，破壞 Persona 治療同盟 (R05 §治療同盟)；M1.2 斷點偵測已確保不在高認知負荷時推送。

❌ **不要讓 NER 解析器在無法確認時猜測時間**
   理由：錯誤的耗時數據會導致草稿失真，使用者核准時發現不對 → 信任崩潰。回傳 `None` 即可。

❌ **不要在 `ai_analysis` 中填入主觀感受或行動建議**
   理由：R08 §五 意圖脫鉤。AI 只填客觀數據與初步觀察，「感受」和「行動」是使用者的微摩擦力欄位。

❌ **不要在 M4.4 內自行用 domain keywords 做遙測-專家匹配**
   理由：字串包含比對極度不準確（誤匹配/遺漏率高）。遙測的語意分類與專家分配統一由 M4.6 Observer 處理。M4.4 只消費 `TelemetrySegmentReport`，不做 domain 匹配。

❌ **不要在背景監測自信度 ≥ 0.7 時仍套問已知資訊**
   理由：使用者會覺得 AI 在裝傻（明明後台已經知道了卻還來問）。自信度門檻 `CONFIDENCE_THRESHOLD = 0.7` 是鐵律，高於此值的時段不觸發套問。

## 9. Open Questions (已決議)

本模組設計之核心開放問題已與使用者拍板決議：

- **草稿排程時間是否可由使用者自訂？**
  * **決策**：**可自訂**。
  * **細節**：預設為凌晨 02:00（與其餘背景排程錯開），使用者可透過 `role_settings.daily_report_time` 自訂排程時間以符合其作息（如夜貓子可調整為 05:00）。

- **套問觸發條件的具體規則？**
  * **決策**：**自信度門檻 + 進入聊天室時回掃觸發**。
  * **細節**：
    1. **遙測數據由 M4.6 Observer 語意分類**：使用者進入某專家的聊天室時，Observer 回掃近期 `raw_tracking_logs`，產出 `TelemetrySegmentReport`（含自信度與 gap 分析），而非由 M4.4 用 domain keywords 做字串比對。
    2. **自信度門檻機制**：`confidence >= 0.7` 的時段不套問（避免 AI 裝傻）；`confidence < 0.7` 的低自信度時段觸發確認性套問；完全空白的 gap（使用者離線/未使用 coOS）觸發活動詢問。
    3. **套問不限於時間**：不只問「花了多久」，也問未覆蓋時段的活動（如「你上午好像沒在線上，有做什麼跟專案相關的事嗎？」）與低自信度時段的內容確認（如「你下午在 Word 裡忙了好一陣子，是在寫報告嗎？」）。
    4. 頻率限制維持「單一 Thread 上限 1 次，cooldown 5 turn」。

- **深夜草稿是否呼叫雲端 LLM (Gemini) 生成？**
  * **決策**：**本地端輕量模型 (Gemma) 與 Eguard 混合生成**。
  * **細節**：為了遵守 L1 明文不下雲的安全規定，草稿的客觀描述與分析先由本地程式碼（Regex 與模板）拼裝，涉及語意摘要則呼叫本地 Gemma (M2.2) 處理，生成 `ai_description` 與 `ai_analysis`。寫入資料庫前必須通過 `M2.3 Eguard` 泛化脫敏。絕不將未經脫敏的 `raw_tracking_logs` 明文送往雲端 Gemini。

- **M1.5 微 Nudges 的回覆如何整合至草稿？**
  * **決策**：**MVP 階段暫時忽略**。
  * **細節**：微 Nudges 回覆的整合較為複雜，首期 MVP 僅聚焦於遙測耗時與對話套問的整合。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責，不能拆解 — 套問 + 草稿生成管線
- [x] §2 至少 1 個 `Rxx` 引用 — R10 ×2, R08 ×3
- [x] §3 Schema 用 dataclass — `ElicitationPromptFragment`, `TelemetrySegmentReport`, `DurationResult`, `DraftReflection`
- [x] §4 依賴是真實模組編號 — M4.1, M4.2, M4.3, M4.6, M6.1, M6.4
- [x] §5 grep 過 `05_integration_risk_audit.md` — RISK-01, RISK-15
- [x] §6 測試先於程式碼 — 16 條驗收測試
- [x] §8 至少 3 條反模式 — 7 條
- [x] §9 至少 1 個開放問題 — 4 個

---

## 附錄：子模組拆分決策

> **結論：M4.4.1~M4.4.3 合併為單一 SPEC，不分開寫。**

| 評估維度 | M4.4 子模組情況 |
| -------- | -------------- |
| **部署邊界** | 全在同一 FastAPI sidecar 內 |
| **技術棧** | 全是 Python (M4.4.1 LangGraph 節點 + M4.4.2 Regex/NLP + M4.4.3 arq Cron) |
| **資料流** | 單向管線：M4.4.1 套問 → M4.4.2 解析 → 暫存 → M4.4.3 深夜拼裝。三者共用 `task_slot` 暫存結構 |
| **耦合度** | 高 — M4.4.3 直接消費 M4.4.1+M4.4.2 白天收集的結構化數據 |
| **獨立部署** | 不可能，M4.4.3 若獨立則缺少 M4.4.1+M4.4.2 的套問數據來源 |
| **時間差異** | M4.4.1+M4.4.2 白天即時；M4.4.3 深夜批次。但這是同一管線的兩個階段，非獨立服務 |
