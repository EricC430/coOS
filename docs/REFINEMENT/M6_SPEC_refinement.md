# M6 規格修訂 (M6 Specification Refinement)
## 支援時段卡片審查、Segment 級 XP 結算與 XP 帳本統計

**標籤**:`[MVP-Refinement]`
**版本**:`1.4-draft`
**最後更新**:2026-05-31
**基礎規格**: 
*   [M6_2_postgresql_schemas_SPEC.md](file:///c:/Users/chent\Desktop/我的資料夾/學校/大學/三下/生成式人工智慧導論/coOS/docs/modules/M6_2_postgresql_schemas_SPEC.md) (雲端 Schema)
*   [M6_3_role_context_tables_SPEC.md](file:///c:/Users/chent\Desktop/我的資料夾/學校/大學/三下/生成式人工智慧導論/coOS/docs/modules/M6_3_role_context_tables_SPEC.md) (角色情境表)
*   [M6_4_daily_reflections_SPEC.md](file:///c:/Users/chent\Desktop/我的資料夾/學校/大學/三下/生成式人工智慧導論/coOS/docs/modules/M6_4_daily_reflections_SPEC.md) (每日反思)
*   [M6_5_acid_gatekeeper_SPEC.md](file:///c:/Users/chent\Desktop/我的資料夾/學校/大學/三下/生成式人工智慧導論/coOS/docs/modules/M6_5_acid_gatekeeper_SPEC.md) (ACID 交易守門員)

---

## 1. 變更目的 (Purpose of Change)

根據最新設計討論，對 `M6` 進行以下調整與欄位擴充：
1.  **核准與 XP 結算的主體下放到 Segment 卡片層級**：
    *   使用者每天為一個角色產生多張時段卡片 (`daily_reflection_segments`)。
    *   卡片審查、XP 計算發放、`is_reviewed` 與 `is_draft` 旗標轉移至 **Segment 卡片** 上。
    *   **審查條件**：在完成一天的反思審查時，該角色當天必須**至少有一個 Segment 卡片**被填寫並核准。其餘 Segments 為選填。
2.  **時段與日反思表延伸指標擴充**：
    *   **行為與專注深度指標**（時段持續分鐘、專注深度、分心次數）。
    *   **反思輔助與心理機制**（反思鷹架引導語、反思字數與時間等投入度指標、整日心情滿意度）。
    *   **任務與外部整合**（任務關聯 ID、外部行事曆事件關聯 ID）。
    *   **遊戲化與激勵機制**（連續完成天數加成倍率、每日總活動時長）。
3.  **XP 系統完整收支流水帳 (XP Ledger) 擴充**：
    *   擴充 `xp_ledger` 表，加入關聯欄位（`role_id`, `expert_id`, `project`, `segment_id`, `task_id`），在 `M6.5` 交易中一併寫入，以利後續的統計查詢。
4.  **M6.3 角色與專案關係調整**：
    *   個人角色新增 **`avatar_url` (頭像)** 欄位以利 UI 渲染。
    *   個人專案（`role_projects`）改由**系統自動偵測/行事曆比對/LLM 推論對話**動態發現，增加 AI 建立旗標與比對關鍵字。
    *   優化 `role_settings` 與 `role_implicit_states` 欄位以支援專注目標管理與情緒模型（Valence-Arousal）。

---

## 2. 資料庫 Schema 調整

### 2.1 每日反思主表與子表 (包含延伸指標欄位)

```sql
-- [修改] daily_reflections (父表) -- 僅作為每日角色反思容器與 AI 整日總覽
CREATE TABLE daily_reflections (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL,
    role_id                 UUID NOT NULL,
    reflection_date         DATE NOT NULL,

    -- === AI 整日總覽 ===
    ai_description          TEXT NOT NULL,
    ai_analysis             TEXT,

    -- === 狀態旗標 (整日流程度是否完成) ===
    is_completed            BOOLEAN NOT NULL DEFAULT FALSE, -- 至少一個子卡片被核准即為 TRUE
    completed_at            TIMESTAMPTZ,

    -- === 全天候狀態統計與遊戲化指標 ===
    overall_mood_score      INTEGER CHECK (overall_mood_score >= 1 AND overall_mood_score <= 10), -- 睡前對一天的整體主觀評分
    total_activity_minutes  INTEGER DEFAULT 0,              -- 當日該角色所有 segments 的累計分鐘數
    streak_multiplier       REAL NOT NULL DEFAULT 1.0,      -- 連續天數加成倍率 (例如連續7天完成日報給予 1.2x)

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id),
    UNIQUE (user_id, role_id, reflection_date)
);

-- [修改] daily_reflection_segments (子表) -- 核准、狀態、XP 結算之主體
CREATE TABLE daily_reflection_segments (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reflection_id           UUID NOT NULL,
    
    -- === 屬性與來源 ===
    project                 TEXT NOT NULL,           -- 所屬專案
    expert_id               UUID,                    -- 關聯 AI 專家 ID (選填，若是專家 chat)
    chat_id                 UUID,                    -- 專家對話 ID (選填)
    source_type             TEXT NOT NULL,           -- 'monitor', 'calendar', 'expert_chat'
    segment_time            TIMESTAMPTZ NOT NULL,    -- 時段時間
    external_ref_id         VARCHAR(255),            -- 外部日曆事件關聯 ID (選填)

    -- === 行為與專注度指標 (由 M1.1/M1.2 收集填入) ===
    duration_minutes        INTEGER DEFAULT 0,       -- 該時段持續時長 (分鐘)
    focus_depth             REAL DEFAULT 1.0,        -- 專注深度評分 (0.0 ~ 1.0)
    distraction_count       INTEGER DEFAULT 0,       -- 中斷/分心次數

    -- === AI 客觀描述與分析 ===
    ai_description          TEXT NOT NULL,
    ai_analysis             TEXT,

    -- === 使用者主觀反思 (微摩擦力) ===
    scaffold_prompt         TEXT,                    -- 當下系統隨機分派的反思鷹架引導語
    user_feeling            TEXT,                    -- 當此卡被核准時必填
    user_action_plan        TEXT,                    -- 當此卡被核准時必填
    user_learned            TEXT,                    -- 使用者學到什麼 (選填)
    is_aligned              BOOLEAN,                 -- 是否與目標對齊
    mood_score              INTEGER CHECK (mood_score >= 1 AND mood_score <= 10),

    -- === 反思投入度指標 (IKEA效應衡量) ===
    reflection_word_count   INTEGER DEFAULT 0,       -- 使用者輸入反思的總字數
    reflection_edit_seconds INTEGER DEFAULT 0,       -- 編輯此反思卡片所花費的時間 (秒)

    -- === 關聯任務 (獨立 UUID，無 Foreign Key 約束，以便未來任務模組對接) ===
    task_id                 UUID,                    -- 關聯 Task ID (選填)

    -- === 卡片核准與 XP 結算狀態 ===
    is_draft                BOOLEAN NOT NULL DEFAULT TRUE,
    is_reviewed             BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at             TIMESTAMPTZ,
    earned_xp               INTEGER DEFAULT 0,
    xp_settled              BOOLEAN NOT NULL DEFAULT FALSE,
    xp_settled_at           TIMESTAMPTZ,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (reflection_id) REFERENCES daily_reflections(id) ON DELETE CASCADE,
    FOREIGN KEY (expert_id) REFERENCES ai_experts(id)
);

CREATE INDEX idx_drs_reflection ON daily_reflection_segments(reflection_id);
CREATE INDEX idx_drs_reviewed ON daily_reflection_segments(is_reviewed);
CREATE INDEX idx_drs_task ON daily_reflection_segments(task_id) WHERE task_id IS NOT NULL;
```

> [!NOTE]
> **關於任務 (Task) 系統的資料表規劃與外鍵處理**：
> 目前 MVP 的資料庫結構中**尚未建立實體 `tasks` 資料表**（目前在 XP Staking 測試中僅使用 fake / mock 資料結構）。
> 為了保留擴充彈性，`daily_reflection_segments.task_id` 與下述 `xp_ledger.task_id` 欄位皆採用**不加 FOREIGN KEY 約束的 UUID 欄位**。
> 當未來 Phase 部署任務管理模組時，可安全地對接該 UUID，亦可視需求透過 Alembic 遷移補上外鍵約束。

### 2.2 經驗值流水帳：`xp_ledger`

```sql
-- [修改] xp_ledger (L3 業務狀態)
CREATE TABLE xp_ledger (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    
    -- === 收入支出數值 ===
    amount          INTEGER NOT NULL CHECK (amount != 0), -- 正數為收入，負數為支出/質押/抽卡扣除
    xp_type         VARCHAR(20) NOT NULL,                 -- 'earned', 'ambient', 'staked', 'spent_gacha', 'penalty'
    reason          VARCHAR(255) NOT NULL,                -- 人類可讀原因
    source_module   VARCHAR(10) NOT NULL,                 -- 'M4.5', 'M4.13', 'M3.11'
    
    -- === 來源細分 (統計用) ===
    role_id         UUID,                                 -- 獲得/扣除時的角色 ID
    expert_id       UUID,                                 -- 獲得/扣除時的專家 ID (適用專家 chat segment)
    project         TEXT,                                 -- 獲得時對應的專案名稱
    segment_id      UUID,                                 -- 對應的時段卡片 ID (若是 segment 審核產生)
    task_id         UUID,                                 -- 關聯 Task ID (若是任務質押或完成挑戰產生)
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (expert_id) REFERENCES ai_experts(id),
    FOREIGN KEY (segment_id) REFERENCES daily_reflection_segments(id) ON DELETE SET NULL
);

CREATE INDEX idx_xl_user ON xp_ledger(user_id);
CREATE INDEX idx_xl_role ON xp_ledger(role_id);
CREATE INDEX idx_xl_expert ON xp_ledger(expert_id);
CREATE INDEX idx_xl_project ON xp_ledger(project);
CREATE INDEX idx_xl_task ON xp_ledger(task_id) WHERE task_id IS NOT NULL;
```

### 2.3 基礎表與角色情境表擴充 (新增與修訂)

```sql
-- [修改] users 表 (L3 業務狀態 - 新增累計總經驗值以防等級因扣減/消費而倒退)
-- 說明：current_xp 作為可用(未花費)經驗值餘額，會隨抽卡/質押扣減；lifetime_xp 則為生涯累計總值，唯增不減，用作等級(level)計算依據。
ALTER TABLE users ADD COLUMN lifetime_xp INTEGER NOT NULL DEFAULT 0;

-- [修改] roles 表 (L3 業務狀態 - 擴充頭像以利 UI 顯示)
-- 說明：儲存個人角色自定義圖像網址，以利在綜合時段卡片時間軸上進行視覺識別與分隔。
ALTER TABLE roles ADD COLUMN avatar_url VARCHAR(512);

-- [確認/修改] ai_experts 表 (L3 業務狀態 - 確保頭像欄位存在)
-- 說明：確認包含 avatar_url 欄位以儲存 AI 專家的頭像或圖示連結。若基於舊版 migration 升級，需補上此欄位：
-- ALTER TABLE ai_experts ADD COLUMN avatar_url VARCHAR(512);

-- [修改] role_projects 表 (L3 業務狀態 - 支援 AI 自動偵測與比對關鍵字)
CREATE TABLE role_projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         UUID NOT NULL,
    name            VARCHAR(100) NOT NULL,
    description     VARCHAR(500),
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed', 'paused', 'archived')),
    
    -- === AI 偵測與判定機制欄位 ===
    inferred_by_ai  BOOLEAN NOT NULL DEFAULT FALSE,      -- 是否為 AI 透過對話/行為偵測發現並建議創建的專案
    alias_keywords  TEXT,                                -- JSON 陣列，存放該專案的比對關鍵字 (例如：["rust", "cargo", "os-lab"])，以利 telemetry 比對

    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- [修改] role_settings 表 (L3 業務狀態 - 支援專注時數目標管理)
CREATE TABLE role_settings (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id                 UUID NOT NULL UNIQUE,
    theme                   VARCHAR(20) DEFAULT 'default',
    notification_enabled    BOOLEAN DEFAULT TRUE,
    daily_report_time       TIME DEFAULT '22:00',
    focus_hours_start       TIME DEFAULT '09:00',
    focus_hours_end         TIME DEFAULT '18:00',
    
    -- === 目標追蹤 ===
    weekly_target_minutes   INTEGER DEFAULT 0,           -- 該身分角色每週預期專注的總時間目標 (分鐘)

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- [修改] role_implicit_states 表 (L2 本地狀態快取 - 情緒維度與可解釋性觸發)
CREATE TABLE role_implicit_states (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    role_id         UUID NOT NULL,
    label           VARCHAR(30) NOT NULL,                -- 狀態標籤 (如 'anxiety', 'flow')
    confidence      REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    
    -- === 情緒環狀模型 (Valence-Arousal Model) ===
    valence         REAL CHECK (valence >= -1.0 AND valence <= 1.0),     -- 正負向度 (愉快-不愉快)
    arousal         REAL CHECK (arousal >= -1.0 AND arousal <= 1.0),     -- 激活度 (興奮-平靜)

    -- === AI 推論可解釋性 ===
    raw_triggers    TEXT,                                -- JSON 陣列，存放觸發此推論的 telemetry 事件型態 (例如：["error_rate_high", "tab_switch_freq_high"])

    inferred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    source_module   VARCHAR(10) NOT NULL DEFAULT 'M4.8',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);
```

### 2.4 本地 SQLite Schema 調整 (M6.1)

為了支援語音副語言特徵分析（M4.2 Paralinguistic cues）與項目檢索過濾（GraphRAG），對本地 SQLite 進行以下欄位擴充：

```sql
-- [修改] chat_transcripts 表 (L1 本地明文 - 擴充專案關聯與語音特徵支援)
-- 說明：
-- 1. project: 關聯特定專案，以便將來按專案過濾歷史對話做 Context 注入或 GraphRAG 檢索。
-- 2. audio_path: 存放本地原始語音檔路徑 (T1 隱私級別，絕不上雲)。
-- 3. paralinguistic_metadata: 存放語音情感特徵 JSON 字串 (如語速、聲調波動、壓力指數，供音調狀態機分析)。
ALTER TABLE chat_transcripts ADD COLUMN project TEXT;
ALTER TABLE chat_transcripts ADD COLUMN audio_path TEXT;
ALTER TABLE chat_transcripts ADD COLUMN paralinguistic_metadata TEXT;
```

---

## 3. 業務驗證邏輯與 ACID 守門員修改

### 3.1 審查函數 (Approve Logic) — 判斷「至少一個卡片必填」
使用者一次提交多張卡片的更新。我們必須檢驗：
1.  該角色當天所有 Segments 之中，**是否有至少一個卡片被成功核准**（填寫了 `user_feeling` 與 `user_action_plan`，且 `is_reviewed` 轉為 `True`）。
2.  若符合條件，更新所有已填寫反思卡片的狀態，並將父表 `daily_reflections` 標記為 `is_completed = True`。

```python
# services/m6_4_daily_reflections/approve.py

from datetime import datetime, UTC

def approve_daily_reflection_flow(
    reflection: DraftReflection,
    segments: list[DraftReflectionSegment],
    updates: list[SegmentUpdateInput]
) -> tuple[DraftReflection, list[DraftReflectionSegment]]:
    """
    [R08 §四.2] 反思審查核心流程。
    驗證：該角色當天至少有一個 Segment 完成了完整的反思 (feeling 與 action_plan)。
    """
    update_map = {up.segment_id: up for up in updates}
    updated_segments = []
    any_approved = False
    total_minutes = 0

    for seg in segments:
        total_minutes += (seg.duration_minutes or 0)
        up = update_map.get(seg.id)
        if not up:
            # 使用者未對此卡片進行編輯，跳過
            updated_segments.append(seg)
            if seg.is_reviewed:
                any_approved = True
            continue

        # 檢驗卡片是否符合核准標準
        has_feeling = bool(up.user_feeling and up.user_feeling.strip())
        has_action_plan = bool(up.user_action_plan and up.user_action_plan.strip())

        if has_feeling and has_action_plan:
            # 符合核准條件
            if not seg.is_draft:
                raise ValueError(f"卡片 {seg.id} 已經是核准狀態，不可重複核准")
            
            seg.user_feeling = up.user_feeling.strip()
            seg.user_action_plan = up.user_action_plan.strip()
            seg.user_learned = up.user_learned.strip() if up.user_learned else None
            seg.is_aligned = up.is_aligned
            seg.mood_score = up.mood_score
            
            # 統計投入度指標
            full_text = f"{seg.user_feeling} {seg.user_action_plan} {seg.user_learned or ''}"
            seg.reflection_word_count = len(full_text.strip())
            seg.reflection_edit_seconds = up.reflection_edit_seconds or 0
            
            seg.is_draft = False
            seg.is_reviewed = True
            seg.reviewed_at = datetime.now(UTC)
            any_approved = True
        elif has_feeling or has_action_plan:
            # 填了一半，不符合核准條件且不應放行 (微摩擦力防呆)
            raise ValueError("填寫反思時，感受 (user_feeling) 與行動計畫 (user_action_plan) 必須同時填寫")
        else:
            # 兩者皆空，代表使用者不想核准此張卡片 (選填)
            if up.user_learned:
                seg.user_learned = up.user_learned.strip()
            seg.is_aligned = up.is_aligned
            seg.mood_score = up.mood_score
            # 依然保持 is_draft = True, is_reviewed = False

        updated_segments.append(seg)

    if not any_approved:
        raise ValueError("當天該角色必須至少核准 (Approve) 一張時段卡片 (Segment Card)")

    # 滿足條件，更新父表狀態
    reflection.is_completed = True
    reflection.completed_at = datetime.now(UTC)
    reflection.total_activity_minutes = total_minutes

    return reflection, updated_segments
```

### 3.2 ACID 交易守門員 (`M6.5`) 升級為 Segment 級別結算
XP 發放時，依據個別 Segment 卡片進行鎖定與處理。

```python
# services/m6_5_acid_gatekeeper/transactions.py

from sqlalchemy import select, update

class XPGatekeeper:
    async def settle_segment_xp(
        self, segment_id: str, user_id: str, amount: int
    ) -> TransactionResult:
        """
        [RISK-01] 時段卡片級別之 XP 結算。
        保證原子性：SELECT FOR UPDATE segment -> 驗證 -> UPDATE user -> INSERT ledger -> COMMIT
        """
        async with self._session.begin():
            # 1. 鎖定並查詢時段卡片
            stmt = select(DailyReflectionSegment).where(DailyReflectionSegment.id == segment_id).with_for_update()
            res = await self._session.execute(stmt)
            segment = res.scalar_one_or_none()
            if not segment:
                return TransactionResult(False, "GATEKEEPER_000", "segment_not_found")

            # 2. 驗證卡片審查狀態
            if segment.is_draft or not segment.is_reviewed:
                return TransactionResult(False, "GATEKEEPER_001", "segment_not_approved")
            if segment.xp_settled:
                return TransactionResult(False, "GATEKEEPER_002", "already_settled")

            # 獲取父表資訊以取得 role_id
            ref_stmt = select(DailyReflection).where(DailyReflection.id == segment.reflection_id)
            ref_res = await self._session.execute(ref_stmt)
            reflection = ref_res.scalar_one()

            # 3. 增加使用者 XP (同時更新可用餘額與生涯累計值，防範等級因扣減而倒退)
            await self._session.execute(
                update(User)
                .where(User.id == user_id)
                .values(
                    current_xp=User.current_xp + amount,
                    lifetime_xp=User.lifetime_xp + amount
                )
            )

            # 4. 寫入收支帳本 (包含角色、專家、專案與卡片關聯)
            ledger_entry = XPLedger(
                user_id=user_id,
                amount=amount,
                xp_type="earned",
                reason=f"segment_reflection_approved_{segment.id}",
                source_module="M4.5",
                role_id=reflection.role_id,
                expert_id=segment.expert_id,
                project=segment.project,
                segment_id=segment_id,
                task_id=segment.task_id
            )
            self._session.add(ledger_entry)

            # 5. 更新卡片狀態
            segment.xp_settled = True
            segment.xp_settled_at = datetime.now(timezone.utc)
            segment.earned_xp = amount

            return TransactionResult(True)
```

---

## 4. XP 帳本統計查詢 (統計與呈現 SQL)

為了在前端儀表板 (`M3.2`) 或週報中呈現使用者的 XP 收支細節，可以使用以下 SQL 聚合方式：

### 4.1 未花費與已花費經驗值 (Unspent vs Spent XP)
*   **目前可用 (未花費) 經驗值**：直接查詢 `users.current_xp`（做為緩存），或者計算帳本總和：
    ```sql
    SELECT SUM(amount) AS unspent_xp FROM xp_ledger WHERE user_id = :user_id;
    ```
*   **總累計獲得經驗值**：
    ```sql
    SELECT SUM(amount) AS total_earned_xp FROM xp_ledger WHERE user_id = :user_id AND amount > 0;
    ```
*   **總消耗 (已花費) 經驗值**：
    ```sql
    SELECT ABS(SUM(amount)) AS total_spent_xp FROM xp_ledger WHERE user_id = :user_id AND amount < 0;
    ```

### 4.2 不同身分角色 (Role) 獲得的經驗值
```sql
SELECT 
    r.display_name AS role_name, 
    SUM(xl.amount) AS total_xp
FROM xp_ledger xl
JOIN roles r ON xl.role_id = r.id
WHERE xl.user_id = :user_id AND xl.amount > 0
GROUP BY r.display_name;
```

### 4.3 不同 AI 專家 (Expert) 獲得的經驗值
```sql
SELECT 
    ae.name AS expert_name, 
    SUM(xl.amount) AS total_xp
FROM xp_ledger xl
JOIN ai_experts ae ON xl.expert_id = ae.id
WHERE xl.user_id = :user_id AND xl.amount > 0
GROUP BY ae.name;
```

### 4.4 不同專案 (Project) 獲得的經驗值
```sql
SELECT 
    project, 
    SUM(amount) AS total_xp
FROM xp_ledger
WHERE user_id = :user_id AND amount > 0 AND project IS NOT NULL
GROUP BY project;
```
