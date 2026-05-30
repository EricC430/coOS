# M6.3 — 角色情境資料表 (Role Context Tables)

**標籤**:`[MVP-Refinement v1.1]`
**版本**:`1.1` / `released`
**最後更新**:2026-05-31

**v1.1 變動**（Phase 1.5 Refinement Sprint）：

- `role_projects.inferred_by_ai` — Boolean，標記由 M2.2 邊緣推論自動發現（非使用者手建）
- `role_projects.alias_keywords` — JSON 字串陣列，專案別名關鍵字，供 GraphRAG 語意匹配使用
- `role_settings.weekly_target_minutes` — 週專注時長目標（分鐘），預設 0（無目標）
- `role_implicit_states.valence` / `arousal` — [R03 §6] Valence-Arousal 情緒圓環，各 [-1.0, 1.0]
- `role_implicit_states.raw_triggers` — JSON 陣列，觸發此情緒狀態的遙測事件清單

**注意**：`role_implicit_states` 為本地 SQLite 專屬（L2，永不上雲）。雲端 migrations 不可觸碰此表。

**Migrations**：`alembic_cloud/versions/20260531_1100`（role_projects/role_settings 擴充）、`alembic/versions/20260531_1200`（role_implicit_states Valence-Arousal）

## 1. Purpose (目的)

定義角色情境 (Role Context) 的完整關聯資料結構,包括角色-Persona 映射、角色-專案 (Project) 綁定、角色特定設定,使 M4.3 角色隔離引擎能以 `role_id` 為沙盒鍵,確保 UI、AI 人設、資料查詢都嚴格限定在當前角色範圍內。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R03 | §6 狀態機移轉 | 角色切換時 Persona 必須完全重置,不可繼承上一角色的狀態 |
| R03 | §人設崩塌 | 角色-Persona 映射確保每個 Persona 只服務單一角色,避免跨角色記憶汙染 |
| (無) | 架構文件 §角色沙盒 | Role_ID 沙盒設計的數據層基礎 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M6.2 `roles` 表 | `roles` row | `{id: "uuid", slug: "csie", display_name: "資工系"}` |
| M6.2 `ai_experts` 表 | `ai_experts` row | `{id: "uuid", name: "Robert", role_id: "..."}` |
| 使用者 UI 操作 | API call | `POST /api/m6_3/role/{role_id}/project` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `role_projects` 資料表 | 見 §7.1 | 角色綁定的專案/課程清單 |
| `role_settings` 資料表 | 見 §7.2 | 角色特定的設定 (通知偏好、UI 主題) |
| `role_implicit_states` 資料表 | 見 §7.3 | 每個角色獨立的隱性狀態快取 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M6.2** (PostgreSQL schemas)：依賴 `roles` 與 `ai_experts` 表的存在
- **M0.3** (.env + Alembic)：依賴 Alembic 遷移機制

### 下游 (誰依賴我)

- **M4.3** (角色情境隔離)：以 `role_id` 查詢當前角色可用的 Persona、專案、設定
- **M4.2** (Persona)：透過 `role_id` → `ai_experts` 映射載入正確的 Persona
- **M4.6** (Observer Agent)：以 `role_id` 隔離萃取的 Project 範圍
- **M3.2** (儀表板)：以 `role_id` 過濾顯示的專案、統計數據
- **M4.8** (隱性狀態推論)：寫入/讀取 `role_implicit_states` (RISK-06)

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-06** | 角色切換時 ImplicitState 跨界洩漏 | `role_implicit_states` 以 `(user_id, role_id)` 雙鍵索引; 切換角色時 M4.2.4 必須只讀當前角色的狀態 |
| (無直接 RISK-xx) | 角色刪除後殘留孤兒 Project/Setting | 所有子表 Foreign Key 設 `ON DELETE CASCADE` |
| (無直接 RISK-xx) | 使用者建立過多角色導致 Supabase 500MB 溢位 | 限制每使用者最多 10 個角色 (CHECK constraint) |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m6_3/test_role_context_tables.py

import pytest


class TestRoleProjectRelation:
    def test_project_belongs_to_role(self, cloud_db, sample_role):
        """驗收條件 1: Project 必須綁定到 role_id"""
        cloud_db.execute(
            "INSERT INTO role_projects (id, role_id, name) "
            "VALUES (gen_random_uuid(), %s, '微積分')",
            (sample_role.id,)
        )
        projects = cloud_db.execute(
            "SELECT * FROM role_projects WHERE role_id = %s",
            (sample_role.id,)
        ).fetchall()
        assert len(projects) == 1

    def test_project_not_visible_across_roles(self, cloud_db, role_csie, role_family):
        """驗收條件 2: 不同角色的 Project 互不可見"""
        cloud_db.execute(
            "INSERT INTO role_projects (id, role_id, name) "
            "VALUES (gen_random_uuid(), %s, 'CSIE專屬')",
            (role_csie.id,)
        )
        family_projects = cloud_db.execute(
            "SELECT * FROM role_projects WHERE role_id = %s",
            (role_family.id,)
        ).fetchall()
        assert len(family_projects) == 0


class TestRoleImplicitState:
    def test_implicit_state_scoped_by_role(self, cloud_db, user, role_csie, role_family):
        """驗收條件 3: [RISK-06] 隱性狀態以 (user_id, role_id) 雙鍵隔離"""
        # 為 CSIE 角色設定焦慮狀態
        cloud_db.execute(
            "INSERT INTO role_implicit_states (id, user_id, role_id, label, confidence) "
            "VALUES (gen_random_uuid(), %s, %s, 'anxiety', 0.85)",
            (user.id, role_csie.id)
        )
        # 查詢 FAMILY 角色的隱性狀態 → 應為空
        family_state = cloud_db.execute(
            "SELECT * FROM role_implicit_states "
            "WHERE user_id = %s AND role_id = %s",
            (user.id, role_family.id)
        ).fetchone()
        assert family_state is None

    def test_role_switch_does_not_inherit_state(self, cloud_db, user, role_csie, role_family):
        """驗收條件 4: [RISK-06] 切換角色後不可繼承上一角色的狀態"""
        cloud_db.execute(
            "INSERT INTO role_implicit_states (id, user_id, role_id, label, confidence) "
            "VALUES (gen_random_uuid(), %s, %s, 'flow', 0.9)",
            (user.id, role_csie.id)
        )
        # 切換到 FAMILY → 查詢當前角色的狀態
        current_state = cloud_db.execute(
            "SELECT label FROM role_implicit_states "
            "WHERE user_id = %s AND role_id = %s "
            "ORDER BY inferred_at DESC LIMIT 1",
            (user.id, role_family.id)
        ).fetchone()
        assert current_state is None  # 不繼承 CSIE 的 flow


class TestCascadeDelete:
    def test_role_delete_cascades_projects(self, cloud_db, sample_role):
        """驗收條件 5: 刪除角色時其下 Project 自動刪除"""
        cloud_db.execute(
            "INSERT INTO role_projects (id, role_id, name) "
            "VALUES (gen_random_uuid(), %s, '將被刪除')",
            (sample_role.id,)
        )
        cloud_db.execute("DELETE FROM roles WHERE id = %s", (sample_role.id,))
        orphans = cloud_db.execute(
            "SELECT * FROM role_projects WHERE role_id = %s",
            (sample_role.id,)
        ).fetchall()
        assert len(orphans) == 0
```

## 7. Implementation Notes

### 7.1 `role_projects` (L3 — 角色綁定專案)

```sql
-- 角色下的專案/課程/目標
CREATE TABLE role_projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         UUID NOT NULL,
    name            VARCHAR(100) NOT NULL,
    description     VARCHAR(500),
    status          VARCHAR(20) NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed', 'paused', 'archived')),
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

CREATE INDEX idx_rp_role ON role_projects(role_id);
```

### 7.2 `role_settings` (L3 — 角色特定設定)

```sql
-- 每個角色的個性化設定 (UI 主題、通知偏好等)
CREATE TABLE role_settings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id         UUID NOT NULL UNIQUE,       -- 每角色一筆
    theme           VARCHAR(20) DEFAULT 'default',
    notification_enabled BOOLEAN DEFAULT TRUE,
    daily_report_time   TIME DEFAULT '22:00',   -- 幾點生成日報草稿
    focus_hours_start   TIME DEFAULT '09:00',   -- 專注時段開始
    focus_hours_end     TIME DEFAULT '18:00',   -- 專注時段結束
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);
```

### 7.3 `role_implicit_states` (L3 — 角色隱性狀態快取)

```sql
-- [RISK-06] 以 (user_id, role_id) 雙鍵隔離的隱性狀態
-- 此表為 M4.8 推論結果的快取, 供 M4.2.4 注入 Persona 使用
CREATE TABLE role_implicit_states (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    role_id         UUID NOT NULL,
    label           VARCHAR(30) NOT NULL,       -- 'anxiety', 'flow', 'avoidance', ...
    confidence      REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    inferred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,               -- 狀態有效期限 (NULL = 不過期直到被新推論覆蓋)
    source_module   VARCHAR(10) NOT NULL DEFAULT 'M4.8',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

CREATE INDEX idx_ris_user_role ON role_implicit_states(user_id, role_id);
CREATE INDEX idx_ris_inferred ON role_implicit_states(inferred_at);
```

### 7.4 Pydantic Models

```python
# services/m6_3_role_context/models.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime, time
from typing import Optional


class RoleProject(BaseModel):
    id: UUID
    role_id: UUID
    name: str = Field(max_length=100)
    description: Optional[str] = Field(max_length=500, default=None)
    status: str = Field(default="active")
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime


class RoleSetting(BaseModel):
    id: UUID
    role_id: UUID
    theme: str = "default"
    notification_enabled: bool = True
    daily_report_time: time = time(22, 0)
    focus_hours_start: time = time(9, 0)
    focus_hours_end: time = time(18, 0)


class RoleImplicitState(BaseModel):
    """[RISK-06] 必須以 (user_id, role_id) 雙鍵查詢"""
    id: UUID
    user_id: UUID
    role_id: UUID
    label: str
    confidence: float = Field(ge=0, le=1)
    inferred_at: datetime
    expires_at: Optional[datetime] = None
    source_module: str = "M4.8"
```

### 7.5 異常處理

- 角色不存在 → `404 Not Found`; 不可 fallback 到其他角色
- Foreign Key 違反 → `IntegrityError`, 前端提示「角色已被刪除」
- 超過 10 個角色上限 → `422 Unprocessable Entity`

## 8. Anti-patterns (反模式)

- ❌ **不要在角色切換時把上一個角色的 `role_implicit_states` 複製到新角色**。切換後若新角色無狀態,回傳 `PersonaContext.neutral_default()`,不可繼承。
  理由:RISK-06 (跨角色資料洩漏)。

- ❌ **不要用 `user_id` 單鍵查詢 `role_implicit_states`** (會拿到所有角色的狀態)。必須用 `(user_id, role_id)` 雙鍵。
  理由:RISK-06。

- ❌ **不要讓 `role_projects` 直接引用 `chat_transcripts`**。`chat_transcripts` 是 L1 本地資料 (M6.1 SQLite),`role_projects` 是 L3 雲端資料。跨層 Foreign Key 不存在。
  理由:架構文件 §3 隱私三層分類; 本地與雲端 DB 之間不可建立 FK。

- ❌ **不要在 `role_settings` 中儲存使用者的工作內容偏好** (如「常用程式語言」「常開的網站」)。這些屬行為特徵 (L1),不可上雲。
  理由:RISK-12 (側通道洩漏)。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [x] **`role_implicit_states` 是存在雲端 PostgreSQL 還是本地 SQLite?** (決策：放在本地 SQLite。隱性狀態（如焦慮、心流）屬高度即時且私密的 L2 狀態，跨裝置不需要同步這些短期狀態，切換裝置時讓推論重新開始即可。)
- [x] **每角色最多幾個 Project?** (決策：不限制數量。Project 的概念類似於標籤 (Label)，不設硬性上限。AI 在聊天 session 中會自動偵測當前對話主題，判斷是匹配現有 Project 還是建議使用者建立新 Project 並標籤化；多個 session 可以共用同一個 Project 標籤。Project 的進階功能（如進度追蹤、Kanban 等）留待未來研議。)
- [x] **`role_settings.daily_report_time` 是 UTC 還是使用者本地時區?** (決策：資料庫統一儲存為 UTC，前後端互動時再轉換為使用者的本地時區，這是處理跨時區最穩健的標準作法。)

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 有 R03 引用 (人設崩塌 + 狀態機移轉)
- [x] §3 Schema 用 SQL DDL + Pydantic 描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,有 RISK-06 對應
- [x] §6 測試先於程式碼
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
