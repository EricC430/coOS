# M6.4 — 每日反思資料表 (Daily Reflections Table)

**標籤**:`[MVP]`
**版本**:`1.0` / `draft`
**最後更新**:2026-05-30

## 1. Purpose (目的)

定義 `daily_reflections` 資料表的完整 schema,作為「草稿與核准」(Draft & Approve) 機制的核心數據載體。此表儲存 AI 自動生成的客觀行為描述 (草稿) 與使用者必須手動填寫的主觀反思 (核准),確保 XP 發放的守門員邏輯有明確的 `is_draft` / `is_reviewed` 欄位可依賴。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §四.2 微摩擦力 | `user_feeling` 與 `user_action_plan` 必填,不可省略 |
| R08 | §五 意圖脫鉤 | AI 填客觀數據 (`ai_description`, `ai_analysis`), 使用者填主觀感受 |
| R08 | §六.1 IKEA 效應 | 使用者付出努力填寫後才發 XP, `is_reviewed = true` 是 XP 的前提 |
| R10 | §MindScape 反思鷹架 | 反思結構源自 MindScape 的結構化反思模板 |
| R10 | §典範轉移 | 從純量化 (數字) 到質性 (文字) 的紀錄模式 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.4 自然套問 / 草稿拼裝 | `DraftReflection` | `{ai_description: "VS Code 3h, Rust...", ai_analysis: "..."}` |
| M4.6 Observer Agent | Project 與任務摘要 | `{projects_touched: ["微積分", "OS Lab"]}` |
| 使用者手動填寫 (M3.3.3) | `UserReflectionInput` | `{user_feeling: "很挫折", user_action_plan: "明天先看教學影片"}` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `daily_reflections` 資料表 | 見 §7.1 | 一行完整的反思記錄 |
| M4.5 XP 結算觸發 | `is_reviewed = true` event | 觸發 M4.5 計算 earned XP |
| M3.3 日報模組 | 讀取並渲染 | 前端顯示草稿 / 已核准的反思列表 |
| M3.8 Wrapped 彈窗 | 週/月統計查詢 | `AVG(mood_score)`, `COUNT(*)` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M6.2** (PostgreSQL schemas)：`daily_reflections` 存放位置待定 (見 §9 Open Questions)
- **M6.1** (SQLite schemas)：若反思含 L1 明文 (使用者主觀感受),可能需存本地
- **M0.3** (.env + Alembic)：依賴 Alembic 遷移機制

### 下游 (誰依賴我)

- **M4.5** (XP 自動結算)：讀取 `is_reviewed` 決定是否發放 XP (RISK-01)
- **M3.3.3** (草稿核准彈窗)：讀取/更新 `is_draft`, `user_feeling`, `user_action_plan`
- **M3.8** (Wrapped 彈窗)：讀取 `mood_score`, `motivation_delta` 做週報 (RISK-10)
- **M6.5** (ACID 守門員)：XP 結算時鎖定 `is_reviewed` 狀態

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-01** | 草稿狀態下 XP 被提前發放 → IKEA 效應失效 | `is_reviewed` 必須為 `true` 且 `user_feeling` 非空才允許 M4.5 結算; M6.5 ACID 守門員強制此約束 |
| **RISK-10** | Wrapped 只看相對提升不看絕對水平 → Gaslighting 感 | `mood_score` 必須作為 Wrapped (M3.8) 的絕對水平基準; 此表提供原始數據 |
| (無直接 RISK-xx) | `user_feeling` 包含敏感心理內容 → 上雲風險 | 若 `daily_reflections` 存雲端,`user_feeling` 與 `user_action_plan` 須考慮是否為 L1 明文 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m6_4/test_daily_reflections.py

import pytest
from datetime import date


class TestDraftApproveLifecycle:
    def test_new_reflection_is_draft(self, db):
        """驗收條件 1: [R08 §五] 新建反思必須是草稿狀態"""
        reflection = create_reflection(
            ai_description="VS Code 寫了 3 小時 Rust",
            ai_analysis="專注度高,但最後 30 分鐘效率下降",
        )
        assert reflection.is_draft is True
        assert reflection.is_reviewed is False
        assert reflection.user_feeling is None
        assert reflection.user_action_plan is None

    def test_approve_requires_user_feeling(self, db):
        """驗收條件 2: [R08 §四.2] 核准必須填寫 user_feeling"""
        reflection = create_reflection(ai_description="...", ai_analysis="...")
        with pytest.raises(ValueError, match="user_feeling"):
            approve_reflection(
                reflection.id,
                user_feeling="",  # 空字串不合法
                user_action_plan="明天先看教學",
            )

    def test_approve_requires_user_action_plan(self, db):
        """驗收條件 3: [R08 §四.2] 核准必須填寫 user_action_plan"""
        reflection = create_reflection(ai_description="...", ai_analysis="...")
        with pytest.raises(ValueError, match="user_action_plan"):
            approve_reflection(
                reflection.id,
                user_feeling="有點挫折",
                user_action_plan="",  # 空字串不合法
            )

    def test_approved_reflection_flips_flags(self, db):
        """驗收條件 4: 核准後 is_draft=False, is_reviewed=True"""
        reflection = create_reflection(ai_description="...", ai_analysis="...")
        approved = approve_reflection(
            reflection.id,
            user_feeling="覺得有進步",
            user_action_plan="繼續保持現在的節奏",
            mood_score=7,
        )
        assert approved.is_draft is False
        assert approved.is_reviewed is True
        assert approved.reviewed_at is not None


class TestXPGating:
    def test_xp_blocked_for_draft(self, db):
        """驗收條件 5: [RISK-01] 草稿狀態下 XP 必不發放"""
        reflection = create_reflection(ai_description="...", ai_analysis="...")
        assert reflection.is_draft is True
        result = can_grant_xp(reflection)
        assert result is False

    def test_xp_allowed_after_review(self, db):
        """驗收條件 6: [RISK-01] 核准後 XP 可發放"""
        reflection = create_reflection(ai_description="...", ai_analysis="...")
        approved = approve_reflection(
            reflection.id,
            user_feeling="OK",
            user_action_plan="繼續",
            mood_score=6,
        )
        result = can_grant_xp(approved)
        assert result is True


class TestMoodScoreConstraints:
    def test_mood_score_range(self, db):
        """驗收條件 7: mood_score 必須在 1-10 範圍內"""
        with pytest.raises(Exception):
            create_reflection(
                ai_description="...", ai_analysis="...",
                mood_score=0,  # 不合法
            )
        with pytest.raises(Exception):
            create_reflection(
                ai_description="...", ai_analysis="...",
                mood_score=11,  # 不合法
            )
```

## 7. Implementation Notes

### 7.1 `daily_reflections` 資料表

```sql
-- [R08 §四~六, RISK-01] 每日反思 — 草稿與核准機制的核心
CREATE TABLE daily_reflections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL,
    role_id             UUID NOT NULL,
    reflection_date     DATE NOT NULL,

    -- === AI 自動生成區 (系統填, 使用者不可修改) ===
    ai_description      TEXT NOT NULL,           -- [R08 §五] 客觀行為描述
    ai_analysis         TEXT,                    -- AI 初步分析 / 觀察
    projects_touched    TEXT,                    -- JSON array of project names
    activity_minutes    INTEGER,                 -- 當日活動總分鐘數
    source_log_ids      TEXT,                    -- JSON array, 指向 raw_tracking_logs.id

    -- === 使用者手動填寫區 (微摩擦力) ===
    user_feeling        TEXT,                    -- [R08 §四.2] 主觀感受 (必填才能核准)
    user_action_plan    TEXT,                    -- [R08 §四.2] 行動計畫 (必填才能核准)
    user_learned        TEXT,                    -- 選填: 今天學到什麼
    mood_score          INTEGER CHECK (mood_score >= 1 AND mood_score <= 10),

    -- === 狀態旗標 ===
    is_draft            BOOLEAN NOT NULL DEFAULT TRUE,
    is_reviewed         BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at         TIMESTAMPTZ,             -- 核准時間戳

    -- === XP 結算關聯 ===
    earned_xp           INTEGER DEFAULT 0,       -- 核准後計算的 XP
    xp_settled          BOOLEAN NOT NULL DEFAULT FALSE,
    xp_settled_at       TIMESTAMPTZ,

    -- === 元資料 ===
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id),

    -- [R08 §六.1] 每角色每天只有一個反思 (防重複)
    UNIQUE (user_id, role_id, reflection_date)
);

CREATE INDEX idx_dr_user_date ON daily_reflections(user_id, reflection_date);
CREATE INDEX idx_dr_role ON daily_reflections(role_id);
CREATE INDEX idx_dr_draft ON daily_reflections(is_draft) WHERE is_draft = TRUE;
CREATE INDEX idx_dr_reviewed ON daily_reflections(is_reviewed);
```

### 7.2 核准流程 (業務邏輯)

```python
# services/m6_4_daily_reflections/approve.py

from datetime import datetime, timezone


async def approve_reflection(
    reflection_id: str,
    user_feeling: str,
    user_action_plan: str,
    mood_score: int | None = None,
    user_learned: str | None = None,
) -> DailyReflection:
    """
    [R08 §四.2 + RISK-01] 核准反思草稿。
    必須滿足:
    1. user_feeling 非空
    2. user_action_plan 非空
    3. mood_score 在 1-10 範圍 (若提供)
    """
    if not user_feeling or not user_feeling.strip():
        raise ValueError("user_feeling 不可為空 [R08 §四.2 微摩擦力]")
    if not user_action_plan or not user_action_plan.strip():
        raise ValueError("user_action_plan 不可為空 [R08 §四.2 微摩擦力]")
    if mood_score is not None and not (1 <= mood_score <= 10):
        raise ValueError("mood_score 必須在 1-10 範圍")

    reflection = await get_reflection(reflection_id)
    if not reflection.is_draft:
        raise ValueError("此反思已核准, 不可重複核准")

    reflection.user_feeling = user_feeling.strip()
    reflection.user_action_plan = user_action_plan.strip()
    reflection.user_learned = user_learned.strip() if user_learned else None
    reflection.mood_score = mood_score
    reflection.is_draft = False
    reflection.is_reviewed = True
    reflection.reviewed_at = datetime.now(timezone.utc)

    await save_reflection(reflection)

    # [RISK-01] 核准後才允許 M4.5 結算
    # M4.5 會主動輪詢 is_reviewed = true 的記錄
    return reflection
```

### 7.3 Pydantic Models

```python
# services/m6_4_daily_reflections/models.py

from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import date, datetime
from typing import Optional


class DailyReflectionCreate(BaseModel):
    """AI 自動建立草稿時的 schema"""
    user_id: UUID
    role_id: UUID
    reflection_date: date
    ai_description: str = Field(min_length=10)
    ai_analysis: Optional[str] = None
    projects_touched: Optional[list[str]] = None
    activity_minutes: Optional[int] = Field(default=None, ge=0)
    source_log_ids: Optional[list[str]] = None


class UserReflectionInput(BaseModel):
    """[R08 §四.2] 使用者核准時必填的欄位"""
    user_feeling: str = Field(min_length=1, description="主觀感受, 不可為空")
    user_action_plan: str = Field(min_length=1, description="行動計畫, 不可為空")
    user_learned: Optional[str] = None
    mood_score: Optional[int] = Field(default=None, ge=1, le=10)

    @field_validator("user_feeling", "user_action_plan")
    @classmethod
    def must_not_be_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("不可只包含空白字元")
        return v.strip()


class DailyReflectionResponse(BaseModel):
    """完整反思記錄 (讀取用)"""
    id: UUID
    user_id: UUID
    role_id: UUID
    reflection_date: date
    ai_description: str
    ai_analysis: Optional[str]
    projects_touched: Optional[list[str]]
    activity_minutes: Optional[int]
    user_feeling: Optional[str]
    user_action_plan: Optional[str]
    user_learned: Optional[str]
    mood_score: Optional[int]
    is_draft: bool
    is_reviewed: bool
    reviewed_at: Optional[datetime]
    earned_xp: int
    xp_settled: bool
    created_at: datetime
    updated_at: datetime
```

### 7.4 異常處理

- 同一使用者同一角色同一天重複建立草稿 → `UNIQUE` 約束拒絕, 返回已存在的草稿
- `mood_score` 超出範圍 → `CHECK` 約束拒絕, 前端提示
- 反思已核准後嘗試再次核准 → 拒絕, 返回 `409 Conflict`
- AI 生成的 `ai_description` 為空 → 拒絕建立草稿, 要求 M4.4 重新生成

## 8. Anti-patterns (反模式)

- ❌ **不要自動將 `is_reviewed` 設為 `true`**。只有使用者明確核准 (填寫 `user_feeling` + `user_action_plan`) 後才可翻轉此旗標。
  理由:CLAUDE.md §不要做的事 第 1 條; RISK-01; R08 IKEA 效應。

- ❌ **不要在 `ai_description` 中存入原始程式碼片段**。只存摘要 (如 "VS Code 寫了 3 小時 Rust, 修改了 5 個檔案"),不可存 diff 內容。
  理由:若 `daily_reflections` 存在雲端,程式碼片段屬 L1 明文,違反隱私三層原則。

- ❌ **不要讓 `mood_score` 成為 XP 的計算因子**。`mood_score` 是使用者的主觀心情記錄,不可與獎勵掛鉤,否則使用者會為了多 XP 虛報心情。
  理由:R05 §諂媚效應; 數據真實性。

- ❌ **不要跳過 `UNIQUE (user_id, role_id, reflection_date)` 約束**。允許同天多筆反思會破壞日報的「一天一份」心理儀式感。
  理由:R08 §六.1 IKEA 效應; 儀式感是微摩擦力的核心。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [ ] **`daily_reflections` 存在雲端 PostgreSQL 還是本地 SQLite?** `user_feeling` 包含使用者心理狀態描述,可能屬 L1 明文。若上雲,需要明確分類。
- [ ] **已核准的反思是否可以事後修改?** 還是核准後就鎖定 (immutable)?若允許修改,XP 是否需要重新計算?
- [ ] **`mood_score` 是否必填?** 目前設計為可選 (nullable),但 M3.8 Wrapped 需要此欄位做統計。若經常為 NULL 會影響 Wrapped 品質。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 有 R08 (3 處), R10 (2 處) 引用
- [x] §3 Schema 用 SQL DDL + Pydantic 描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,有 RISK-01, RISK-10 對應
- [x] §6 測試先於程式碼
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
