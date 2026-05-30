# M6.2 — 雲端 PostgreSQL Schema 定義 (Cloud PostgreSQL Schemas)

**標籤**:`[MVP-Refinement v1.1]`
**版本**:`1.1` / `released`
**最後更新**:2026-05-31

**v1.1 變動**（Phase 1.5 Refinement Sprint）：

| 項目 | v1.0 | v1.1 |
|------|------|------|
| `users` | `current_xp`, `level`... | 新增 `lifetime_xp` [RISK-14] |
| `roles` | `display_name`... | 新增 `avatar_url` |
| `xp_ledger` | `user_id`, `amount`... | 新增 FK: `expert_id`, `project`, `segment_id`, `task_id` |
| `role_projects` | 基礎欄 | 新增 `inferred_by_ai`, `alias_keywords` |
| `role_settings` | 基礎欄 | 新增 `weekly_target_minutes` |
| RLS | 無 | 全表啟用 Row Level Security（`auth.uid()` 隔離）|

- `lifetime_xp` — [RISK-14] 唯增不減，等級計算依據；`current_xp` 為可花費餘額
- `avatar_url` — UI 角色頭像渲染，最長 512 字元
- `expert_id` / `project` / `segment_id` — xp_ledger 統計維度，支援按時段/專案/專家聚合
- `inferred_by_ai` — 標記由 M2.2 邊緣推論自動發現的專案
- RLS — 10 張表全部啟用，使用者僅能讀寫自己的資料（`auth.uid()`）

**新增 Pydantic models**：`services/m6_2_postgresql/models.py`（全 L3 表完整覆蓋）

**Migrations**：`alembic_cloud/versions/20260531_1100`（schema 擴充）、`20260531_1200`（RLS）

## 1. Purpose (目的)

定義所有存放於雲端 PostgreSQL (Supabase) 的 L3 業務狀態資料表 schema,涵蓋使用者帳號 (`users`)、AI 專家人設 (`ai_experts`)、XP/徽章/成就等遊戲化狀態,確保跨裝置同步的資料有明確的結構化定義,且絕不包含 L1/L2 隱私資料。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| (無) | 架構文件 §3 隱私三層分類 | T3 業務狀態 → PostgreSQL |
| R06 | §第七章 差分隱私 | 雲端資料表若包含行為統計 (如 XP),須確認不可反推明文 |
| R03 | §1 微觀認知架構 | `ai_experts` 表的 `personality_prompt` 結構源於 BDI 框架 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M0.3 Alembic migration (cloud) | Python migration script | `001_create_users.py` |
| M0.3 Settings | `config.supabase_url`, `config.supabase_key` | Supabase 連線資訊 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `users` 資料表 | 見 §7.1 | 使用者帳號與全域狀態 |
| `ai_experts` 資料表 | 見 §7.2 | Persona 定義 (personality_prompt, trust_level) |
| `roles` 資料表 | 見 §7.3 | 角色定義 (CSIE, FAMILY, ...) |
| `xp_ledger` 資料表 | 見 §7.4 | XP 異動流水帳 |
| `badges` 資料表 | 見 §7.5 | 徽章定義與解鎖紀錄 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.1** (Monorepo)：依賴 `services/alembic/` 結構
- **M0.3** (.env + Alembic)：依賴 `alembic_cloud.ini` 與 Supabase credential

### 下游 (誰依賴我)

- **M4.1** (Agent 路由)：讀取 `ai_experts` 決定路由到哪個 Persona
- **M4.2** (Persona)：讀取 `ai_experts.personality_prompt` 與 `trust_level`
- **M4.3** (角色隔離)：讀取 `roles` 決定可用 Persona 清單
- **M4.5** (XP 結算)：寫入 `xp_ledger`
- **M3.2** (儀表板)：讀取 `users` 的 XP/等級顯示
- **M3.7** (社群模組)：讀取 `users` 的公開資訊
- **M6.3** (角色情境表)：依賴 `roles` 表的定義
- **M6.5** (ACID 守門員)：在 `xp_ledger` 上執行交易

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-12** | Observer 推論成就上雲 → 側通道洩漏 | `badges` / `xp_ledger` 只記錄「業務結果」,不記錄觸發來源的行為明文; 成就 `description` 由使用者核准 |
| (無直接 RISK-xx) | Supabase Free tier 500MB 上限 | XP 流水帳按月歸檔; `ai_experts.personality_prompt` 限 4KB |
| (無直接 RISK-xx) | 雲端 DB 連線失敗 → 本地無法結算 XP | MVP 階段雲端非必要; XP 結算先寫入本地 SQLite 暫存, 恢復連線後同步 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m6_2/test_postgresql_schemas.py

import pytest


class TestCloudTableCreation:
    def test_users_table_exists(self, cloud_db):
        """驗收條件 1: users 表在 cloud migration 後存在"""
        result = cloud_db.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'users')"
        )
        assert result.fetchone()[0] is True

    def test_ai_experts_table_exists(self, cloud_db):
        """驗收條件 2: ai_experts 表存在"""
        result = cloud_db.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'ai_experts')"
        )
        assert result.fetchone()[0] is True

    def test_xp_ledger_table_exists(self, cloud_db):
        """驗收條件 3: xp_ledger 表存在"""
        result = cloud_db.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_name = 'xp_ledger')"
        )
        assert result.fetchone()[0] is True


class TestCloudSchemaConstraints:
    def test_users_has_uuid_primary_key(self, cloud_db):
        """驗收條件 4: users.id 是 UUID 型別"""
        result = cloud_db.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'users' AND column_name = 'id'"
        )
        assert result.fetchone()[0] == "uuid"

    def test_ai_experts_personality_prompt_max_length(self, cloud_db):
        """驗收條件 5: ai_experts.personality_prompt 限制 4KB"""
        # 嘗試插入超過 4KB 的 personality_prompt 應失敗
        long_prompt = "x" * 5000
        with pytest.raises(Exception):  # CHECK constraint 或 VARCHAR 限制
            cloud_db.execute(
                "INSERT INTO ai_experts (id, name, personality_prompt) "
                "VALUES (gen_random_uuid(), 'test', %s)",
                (long_prompt,)
            )

    def test_xp_ledger_amount_must_be_nonzero(self, cloud_db):
        """驗收條件 6: xp_ledger.amount 不可為 0"""
        with pytest.raises(Exception):
            cloud_db.execute(
                "INSERT INTO xp_ledger (id, user_id, amount, reason) "
                "VALUES (gen_random_uuid(), gen_random_uuid(), 0, 'test')"
            )


class TestPrivacyBoundary:
    def test_no_l1_tables_in_cloud(self, cloud_db):
        """驗收條件 7: 雲端 DB 絕不包含 L1 資料表"""
        result = cloud_db.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        table_names = {row[0] for row in result.fetchall()}
        l1_tables = {"raw_tracking_logs", "chat_transcripts", "edge_event_buffer"}
        assert l1_tables.isdisjoint(table_names), \
            f"雲端 DB 中發現 L1 資料表: {l1_tables & table_names}"
```

## 7. Implementation Notes

### 7.1 `users` (L3 — 跨裝置同步)

```sql
-- [架構文件 §3 T3 業務狀態]
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name    VARCHAR(50) NOT NULL,
    email           VARCHAR(255) UNIQUE,   -- 可選, 用於跨裝置同步
    current_xp      INTEGER NOT NULL DEFAULT 0,
    level           INTEGER NOT NULL DEFAULT 1,
    streak_days     INTEGER NOT NULL DEFAULT 0,
    active_role_id  UUID,                  -- 當前啟用的角色
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 7.2 `ai_experts` (L3 — Persona 定義)

```sql
-- [R03 §1, R09 §6.2 BDI] Persona 人設定義
CREATE TABLE ai_experts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(100) NOT NULL,      -- '動力導師_Robert'
    role_id             UUID NOT NULL,               -- 綁定角色
    personality_prompt  VARCHAR(4096) NOT NULL,      -- [R03 §1.1] 固定人設提示詞
    backstory           VARCHAR(2048),               -- 過往經歷腳本
    tone_default        VARCHAR(20) NOT NULL DEFAULT 'authoritative',
    trust_level         REAL NOT NULL DEFAULT 0.5,   -- [0, 1] 信任等級
    avatar_url          VARCHAR(512),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- [R03 §1.1] 每個角色下的 Persona 名稱不重複
CREATE UNIQUE INDEX idx_ae_role_name ON ai_experts(role_id, name);
```

### 7.3 `roles` (L3 — 角色定義)

```sql
-- [架構文件 §角色沙盒] 角色情境定義
CREATE TABLE roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    slug            VARCHAR(30) NOT NULL,      -- 'csie', 'family', 'side_project'
    display_name    VARCHAR(50) NOT NULL,      -- '資工系', '家庭', '副業'
    color_hex       CHAR(7),                   -- UI 標識色 '#FF6B35'
    icon_name       VARCHAR(30),               -- 前端圖示名稱
    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (user_id, slug)
);
```

### 7.4 `xp_ledger` (L3 — XP 異動流水帳)

```sql
-- [RISK-01, CLAUDE.md §6] XP 流水帳 — 每次 XP 異動都必須有記錄
CREATE TABLE xp_ledger (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    role_id         UUID,                      -- XP 歸屬角色 (可為 NULL = 全域)
    amount          INTEGER NOT NULL CHECK (amount != 0),  -- 正數 = 獲得, 負數 = 扣除
    xp_type         VARCHAR(20) NOT NULL,      -- 'earned', 'ambient', 'staked', 'penalty'
    reason          VARCHAR(255) NOT NULL,     -- 人類可讀原因
    source_module   VARCHAR(10) NOT NULL,      -- 'M4.5', 'M4.13', ...
    reflection_id   UUID,                      -- 若為 earned XP, 指向 daily_reflections
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_xl_user ON xp_ledger(user_id);
CREATE INDEX idx_xl_created ON xp_ledger(created_at);
CREATE INDEX idx_xl_type ON xp_ledger(xp_type);
```

### 7.5 `badges` (L3 — 徽章)

```sql
-- 徽章定義與使用者解鎖記錄
CREATE TABLE badge_definitions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(50) UNIQUE NOT NULL,
    display_name    VARCHAR(100) NOT NULL,
    description     VARCHAR(255),
    icon_url        VARCHAR(512),
    category        VARCHAR(30) NOT NULL,      -- 'streak', 'skill', 'hidden'
    is_hidden       BOOLEAN NOT NULL DEFAULT FALSE,  -- [M4.12] 隱藏成就
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_badges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    badge_id        UUID NOT NULL,
    unlocked_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (badge_id) REFERENCES badge_definitions(id),
    UNIQUE (user_id, badge_id)  -- 同徽章不重複解鎖
);
```

### 7.6 異常處理

- Supabase 連線失敗 → 啟動不 crash; 本地暫存 XP 異動, 恢復連線後同步
- UUID 衝突 (極低機率) → PostgreSQL `gen_random_uuid()` 衝突時 retry 一次
- `personality_prompt` 超過 4096 字元 → 拒絕寫入, 提示縮減提示詞

## 8. Anti-patterns (反模式)

- ❌ **不要在雲端 PostgreSQL 中建立 `raw_tracking_logs` 或 `chat_transcripts`**。這些是 L1 明文資料,只能存在於本地 SQLite (M6.1)。
  理由:架構文件 §3 隱私三層分類。

- ❌ **不要在 `xp_ledger` 中記錄觸發 XP 的原始行為描述**。只記錄業務結果 (如 `reason: "daily_reflection_approved"`),不可寫入 `"使用者在 VS Code 寫了 3 小時 Rust"` 之類的行為細節。
  理由:RISK-12 (側通道洩漏); XP 結果上雲不可反推行為模式。

- ❌ **不要用 SERIAL/BIGSERIAL 自增主鍵**。一律使用 UUID。
  理由:與本地 SQLite 的 UUID 策略一致; 未來跨裝置同步時 SERIAL 會衝突。

- ❌ **不要跳過 `xp_ledger.source_module` 欄位**。每筆 XP 異動必須可追溯到是哪個模組發放/扣除的。
  理由:當 RISK-01 發生時 (XP 提前發放), 需要能快速定位是 M4.5 繞過了 M3.3.3。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [x] **`users.email` 是否必填?** (決策：設為可選 (optional) 但介面上可以先收集與保存，為未來的跨裝置登入與雲端備份機制鋪路。)
- [x] **`ai_experts` 的初始種子資料由誰提供?** (決策：三層機制——(1) **內建種子 (Seed data)**：透過 seed script 或 initial migration 預載幾個標準 Persona (如 Robert 等)，確保開箱即用；(2) **自然名稱產生模組**：新建 Persona 時，系統呼叫 LLM 產生自然且不重複的專家名稱 (不可每個都叫同名)，搭配 `UNIQUE INDEX idx_ae_role_name` 確保角色內唯一；(3) **主題偵測配對模組**：在 AI 聊天過程中偵測到新的學科/領域主題時，系統建議使用者配對（或新建）一位該領域的專家 Persona，經使用者同意後動態生成 `personality_prompt` 與 `backstory` 寫入 `ai_experts` 表。上述 (2)(3) 的 SPEC 細節歸屬 M4.1 路由 / M4.2 Persona 模組，此處僅定義資料表結構。)
- [x] **`xp_ledger` 是否需要按月分區 (table partitioning)?** (決策：MVP 階段暫不需要分區，保持架構簡單。Supabase Free tier 500MB 足以應付初期測試，資料量成長後再做歸檔或分區。)

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 有 R06, R03 引用
- [x] §3 Schema 用 SQL DDL 描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,有 RISK-12 對應
- [x] §6 測試先於程式碼
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
