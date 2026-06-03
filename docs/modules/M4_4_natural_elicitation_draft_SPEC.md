# M4.4 — 自然套問與草稿生成器 (Natural Elicitation & Draft Generator)

**標籤**:`[MVP]`
**版本**:`1.0` / `draft`
**最後更新**:2026-06-03

## 1. Purpose (目的)

透過兩階段管線產出每日反思草稿：白天在 Persona 對話中自然套問耗時資訊並解析結構化數據；深夜排程自動拉取 `raw_tracking_logs` 拼裝吉布斯反思循環草稿，寫入 `daily_reflections` 且標記 `is_draft = true`。

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
| M6.1 `raw_tracking_logs` | DB Rows | 前一日所有 `module='M1.*'` 的遙測事件 |
| M6.1 `chat_transcripts` | DB Rows | 前一日所有對話記錄 (含已套問到的耗時) |
| M1.5 微 Nudges 回覆 (若有) | `NudgeResponse` | `{"target_alignment": true, "role_id": "role_csie"}` |
| M4.3 `RoleContext` | 角色上下文 | 決定草稿歸屬角色、專案範圍 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.2 Persona Prompt 注入 | `ElicitationPromptFragment` | `{"inject_question": "這個作業花了多久?", "context": "user_mentioned_homework"}` |
| M6.1 `chat_transcripts` (套問結果) | 標記 `elicitation_tag` | 標記哪些對話 turn 是套問結果 |
| M6.4 `daily_reflections` | `DraftReflection` | `{is_draft: true, ai_description: "...", ai_analysis: "...", source_log_ids: [...]}` |
| M0.4 結構化日誌 | `LogEvent` | 記錄套問觸發、解析結果、草稿生成事件 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.1** (Agent 路由)：套問注入透過 LangGraph 節點觸發
- **M4.2** (Persona 狀態機)：套問問句由 Persona 的語氣包裝，不可破壞人設
- **M4.3** (角色隔離)：草稿嚴格歸屬當前 `role_id`
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
| (無直接 RISK-xx) | 套問頻率過高 → 使用者覺得被審問 | 每次對話最多套問 1 次耗時；cooldown 至少 5 個 turn |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m4_4/test_natural_elicitation_draft.py

import pytest
from datetime import date, time

class TestM4_4_1_ElicitationController:
    def test_elicitation_injected_naturally(self):
        """套問問句必須由 Persona 語氣包裝，不可突兀"""
        fragment = elicitation_controller.generate_question(
            context="user_mentioned_homework",
            persona_tone="empathetic"
        )
        assert fragment.inject_question is not None
        assert len(fragment.inject_question) > 5
        # 不可出現機器式語句
        assert "請輸入耗時" not in fragment.inject_question

    def test_elicitation_cooldown(self):
        """每次對話最多套問 1 次，cooldown 至少 5 turn"""
        controller = ElicitationController()
        controller.record_elicitation(thread_id="t_001", turn=3)
        assert controller.can_elicit(thread_id="t_001", current_turn=5) is False
        assert controller.can_elicit(thread_id="t_001", current_turn=9) is True

    def test_elicitation_scoped_by_role(self):
        """[RISK-06] 套問只針對當前角色的專案"""
        fragment = elicitation_controller.generate_question(
            context="user_mentioned_project",
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
    def test_daily_draft_generated_at_0300(self):
        """每日 03:00 自動產出前一日草稿"""
        with freeze_time("2026-06-03 03:00:00"):
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

```python
# services/m4_4_elicitation/controller.py
# [R08 §五 意圖脫鉤] 套問由 Persona 自然帶出

from dataclasses import dataclass

@dataclass
class ElicitationPromptFragment:
    inject_question: str
    context: str
    target_role_id: str
    cooldown_turns: int = 5

ELICITATION_TEMPLATES = {
    "homework_duration": "對了，{project_name}這個作業大概花了你多久？",
    "coding_session":   "今天寫程式的感覺怎樣？大概寫了多久？",
    "general_task":     "這件事情花了你蠻多時間嗎？",
}

class ElicitationController:
    """每個 thread 最多套問 1 次，cooldown 5 turn"""
    MAX_PER_THREAD = 1
    COOLDOWN_TURNS = 5

    def __init__(self):
        self._history: dict[str, list[int]] = {}  # thread_id → [turn_numbers]

    def can_elicit(self, thread_id: str, current_turn: int) -> bool:
        history = self._history.get(thread_id, [])
        if len(history) >= self.MAX_PER_THREAD:
            return False
        if history and (current_turn - history[-1]) < self.COOLDOWN_TURNS:
            return False
        return True

    def generate_question(self, context: str, persona_tone: str,
                          role_id: str, project_name: str = "") -> ElicitationPromptFragment:
        template = ELICITATION_TEMPLATES.get(context, ELICITATION_TEMPLATES["general_task"])
        question = template.format(project_name=project_name)
        return ElicitationPromptFragment(
            inject_question=question,
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
    每日 03:00 排程。
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

## 9. Open Questions

- [ ] **草稿排程時間是否可由使用者自訂?** 目前硬編碼 03:00，但若使用者作息不同 (如夜貓子 05:00 才睡)，需要可配置。`role_settings.daily_report_time` 已預留此欄位 (M6.3)。
- [ ] **套問觸發條件的具體規則?** 目前設計為「使用者提及作業/專案相關關鍵字」時觸發。是否需要更細緻的規則 (如只在對話超過 3 turn 後才套問)?
- [ ] **深夜草稿是否呼叫雲端 LLM (Gemini) 生成?** 若用 Gemini 生成 `ai_description`/`ai_analysis`，品質更高但涉及隱私 (raw_tracking_logs 送雲端)。是否僅用本地模板拼裝?
- [ ] **M1.5 微 Nudges 的回覆如何整合至草稿?** M1.5 是 `[進階]` 模組，MVP 階段是否先忽略微 Nudges 數據來源?

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責，不能拆解 — 套問 + 草稿生成管線
- [x] §2 至少 1 個 `Rxx` 引用 — R10 ×2, R08 ×3
- [x] §3 Schema 用 dataclass — `ElicitationPromptFragment`, `DurationResult`, `DraftReflection`
- [x] §4 依賴是真實模組編號 — M4.1, M4.2, M4.3, M6.1, M6.4
- [x] §5 grep 過 `05_integration_risk_audit.md` — RISK-01, RISK-15
- [x] §6 測試先於程式碼 — 13 條驗收測試
- [x] §8 至少 3 條反模式 — 5 條
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
