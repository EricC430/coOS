# M6.1 — 本地 SQLite Schema 定義 (Local SQLite Schemas)

**標籤**:`[MVP-Refinement v1.2]`
**版本**:`1.2`
**最後更新**:2026-06-03

**v1.2 變動**（M4.1 自適應路由更新）：

- 新增 `role_router_rules` 表（§7.6）：M4.1.5 自適應規則更新器的規則儲存，以 `role_id` 嚴格隔離
- 新增 `routing_samples` 表（§7.7）：M4.1.1 信心分路由的訓練信號收集，只存 SHA-256 hash，不存明文

**v1.1 變動**（Phase 1.5 Refinement Sprint）：

- `chat_transcripts`：v1.0 基礎欄 → v1.1 新增 `project`, `audio_path`, `paralinguistic_metadata`
- `role_implicit_states`：v1.0 `label`, `confidence` → v1.1 新增 `valence`, `arousal`, `raw_triggers`

- `project` — GraphRAG 過濾用的專案標籤，支援跨時段語境關聯
- `audio_path` — [L1 local-only] 語音附件本地路徑，**永不上雲**
- `paralinguistic_metadata` — JSON，存 `{tempo, pitch_variance, stress_index}`，M4.2 語調狀態機輸入
- `valence / arousal` — [R03 §6] Valence-Arousal 情緒圓環模型，[-1.0, 1.0]，供 M2.2 邊緣推論使用
- `raw_triggers` — JSON 陣列，觸發情緒狀態的遙測事件清單

**新增 Pydantic models**：`services/m6_1_sqlite/models.py`（`ChatTranscriptRead/Create`、`RoleImplicitStateRead/Create` 完整覆蓋）

**Migrations**：`alembic/versions/20260531_1000`（chat_transcripts）、`20260531_1200`（role_implicit_states v1.1）

## 1. Purpose (目的)

定義所有僅存在於本地 SQLite (`data/coos.db`) 的資料表 schema,涵蓋 L1 明文資料 (raw_tracking_logs, chat_transcripts) 與 L2 邊緣推論暫存 (edge_event_buffer),確保隱私三層分類中「絕對不上雲」的資料有明確的結構化定義。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| (無) | 架構文件 §2 資料流四階段 | SQLite 作為「擷取」階段的落地儲存 |
| (無) | 架構文件 §3 隱私三層分類 | T1 明文 + T2 意圖向量均儲存於本地 SQLite |
| R06 | §第七章 差分隱私 | 未來 M2.4 差分隱私微調時需讀取此處 raw data |

> 本模組主要屬基礎設施。R06 引用僅為標記資料表設計需預留差分隱私欄位的可能性。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M0.3 Alembic migration | Python migration script | `001_create_raw_tracking_logs.py` |
| M0.3 Settings | `config.local_db_path` | `../data/coos.db` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `raw_tracking_logs` 資料表 | 見 §7.1 | M0.4 寫入的結構化事件 |
| `edge_event_buffer` 資料表 | 見 §7.2 | M2.2 邊緣推論後的意圖向量暫存 |
| `chat_transcripts` 資料表 | 見 §7.3 | M4.2 對話逐字稿 (L1 明文) |
| `user_consents` 資料表 | 見 §7.4 | 使用者隱私同意記錄 |
| `role_router_rules` 資料表 | 見 §7.6 | M4.1.5 自適應路由規則（依 role_id 隔離） |
| `routing_samples` 資料表 | 見 §7.7 | M4.1.1 路由訓練信號（僅存 hash） |

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.1** (Monorepo)：依賴 `data/` 目錄與 `services/alembic/` 結構
- **M0.3** (.env + Alembic)：依賴 Alembic 遷移機制建立資料表

### 下游 (誰依賴我)

- **M0.4** (結構化日誌)：寫入 `raw_tracking_logs`
- **M2.2** (Gemma 邊緣推論)：寫入/讀取 `edge_event_buffer`
- **M4.2** (Persona)：寫入 `chat_transcripts`
- **M4.6** (Observer Agent)：讀取 `raw_tracking_logs` + `chat_transcripts` 萃取意圖
- **M4.8** (隱性狀態推論)：讀取 `raw_tracking_logs` 進行行為分析
- **M5.2** (NSVIF)：讀取 `raw_tracking_logs` 做反溯因驗證 (RISK-05)
- **M6.4** (daily_reflections)：部分反思草稿的原始依據來自此處
- **M4.1.1** (信心分路由引擎)：寫入 `routing_samples`；啟動時熱載入 `role_router_rules`
- **M4.1.5** (自適應規則更新器)：讀取 `routing_samples` + `daily_reflections`；更新 `role_router_rules`

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-05** | 意圖向量壓縮後 NSVIF 無法反溯因 → 圖譜空洞化 | `edge_event_buffer` 必須保留 `source_log_id` 指向 `raw_tracking_logs`; NSVIF 驗證走本地路徑 |
| (無直接 RISK-xx) | SQLite 單 writer 鎖定導致並發寫入失敗 | 啟用 WAL 模式 (`PRAGMA journal_mode=WAL`); 寫入走 M0.4 的非同步佇列批次寫入 |
| (無直接 RISK-xx) | 資料庫檔案過大 (>1GB) 影響效能 | `raw_tracking_logs` 保留 30 天; `edge_event_buffer` 上推成功後清除; 定期 VACUUM |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m6_1/test_sqlite_schemas.py

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestTableCreation:
    def test_raw_tracking_logs_table_exists(self, local_db):
        """驗收條件 1: raw_tracking_logs 表在 migration 後存在"""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='raw_tracking_logs'"
        )
        assert cursor.fetchone() is not None

    def test_edge_event_buffer_table_exists(self, local_db):
        """驗收條件 2: edge_event_buffer 表存在"""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='edge_event_buffer'"
        )
        assert cursor.fetchone() is not None

    def test_chat_transcripts_table_exists(self, local_db):
        """驗收條件 3: chat_transcripts 表存在"""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_transcripts'"
        )
        assert cursor.fetchone() is not None

    def test_user_consents_table_exists(self, local_db):
        """驗收條件 4: user_consents 表存在"""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_consents'"
        )
        assert cursor.fetchone() is not None

    def test_raw_content_stores_table_exists(self, local_db):
        """驗收條件 4.1: raw_content_stores 表存在"""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='raw_content_stores'"
        )
        assert cursor.fetchone() is not None

    def test_role_router_rules_table_exists(self, local_db):
        """驗收條件 4.2: role_router_rules 表存在 (M4.1.5)"""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='role_router_rules'"
        )
        assert cursor.fetchone() is not None

    def test_routing_samples_table_exists(self, local_db):
        """驗收條件 4.3: routing_samples 表存在 (M4.1.1)"""
        cursor = local_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='routing_samples'"
        )
        assert cursor.fetchone() is not None

    def test_routing_samples_no_raw_msg_column(self, local_db):
        """[RISK-13] routing_samples 不得有儲存原始訊息的欄位"""
        cursor = local_db.execute("PRAGMA table_info(routing_samples)")
        columns = {row[1] for row in cursor.fetchall()}
        forbidden = {"user_msg", "raw_message", "content", "message_text"}
        assert columns.isdisjoint(forbidden), f"發現禁止欄位: {columns & forbidden}"

    def test_role_router_rules_scoped_by_role(self, local_db):
        """[RISK-06] role_router_rules 查詢必須以 role_id 為條件才回傳結果"""
        local_db.execute(
            "INSERT INTO role_router_rules (role_id, pattern, target_domain) "
            "VALUES ('role_csie', '微積分', 'math_tutor')"
        )
        local_db.commit()
        cursor = local_db.execute(
            "SELECT * FROM role_router_rules WHERE role_id='role_family'"
        )
        assert cursor.fetchone() is None


class TestSchemaConstraints:
    def test_raw_tracking_logs_has_required_columns(self, local_db):
        """驗收條件 5: raw_tracking_logs 包含所有必要欄位"""
        cursor = local_db.execute("PRAGMA table_info(raw_tracking_logs)")
        columns = {row[1] for row in cursor.fetchall()}
        required = {"id", "timestamp", "module", "action", "level", "payload"}
        assert required.issubset(columns)

    def test_raw_content_stores_has_required_columns(self, local_db):
        """驗收條件 5.1: raw_content_stores 包含所有必要欄位"""
        cursor = local_db.execute("PRAGMA table_info(raw_content_stores)")
        columns = {row[1] for row in cursor.fetchall()}
        required = {"id", "content_raw", "created_at"}
        assert required.issubset(columns)

    def test_edge_event_buffer_has_source_log_id(self, local_db):
        """驗收條件 6: edge_event_buffer 必須有 source_log_id (RISK-05)"""
        cursor = local_db.execute("PRAGMA table_info(edge_event_buffer)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "source_log_id" in columns

    def test_chat_transcripts_role_is_constrained(self, local_db):
        """驗收條件 7: chat_transcripts.role 只接受 user/assistant/system"""
        # 插入不合法的 role 應失敗 (CHECK constraint)
        import pytest
        with pytest.raises(sqlite3.IntegrityError):
            local_db.execute(
                "INSERT INTO chat_transcripts (id, thread_id, role, content) "
                "VALUES ('test', 'thread_1', 'invalid_role', 'hello')"
            )


class TestWALMode:
    def test_sqlite_wal_mode_enabled(self, local_db):
        """驗收條件 8: SQLite 必須啟用 WAL 模式"""
        cursor = local_db.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"
```

## 7. Implementation Notes

### 7.1 `raw_tracking_logs` (L1 — 絕不上雲)

```sql
-- [架構文件 §3 T1 明文] 原始事件日誌
CREATE TABLE raw_tracking_logs (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,        -- ISO 8601 UTC
    module          TEXT NOT NULL,        -- 'M4.2', 'M1.1', ...
    action          TEXT NOT NULL,        -- 事件動作
    level           TEXT NOT NULL DEFAULT 'INFO',
    payload         TEXT NOT NULL,        -- JSON string (摘要, 非明文)
    user_id         TEXT,
    role_id         TEXT,
    correlation_id  TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_rtl_module ON raw_tracking_logs(module);
CREATE INDEX idx_rtl_timestamp ON raw_tracking_logs(timestamp);
CREATE INDEX idx_rtl_correlation ON raw_tracking_logs(correlation_id);
CREATE INDEX idx_rtl_level ON raw_tracking_logs(level);
```

### 7.2 `edge_event_buffer` (L2 — 意圖向量暫存)

```sql
-- [架構文件 §3 T2 意圖向量] 邊緣推論結果暫存
CREATE TABLE edge_event_buffer (
    id              TEXT PRIMARY KEY,
    source_log_id   TEXT NOT NULL,        -- [RISK-05] 指向 raw_tracking_logs.id
    intent_tag      TEXT NOT NULL,        -- 意圖標籤 (e.g., "coding_frustration")
    intent_vector   BLOB,                 -- 軟提示詞向量 (binary)
    confidence      REAL NOT NULL,        -- 推論信心 [0, 1]
    model_version   TEXT NOT NULL,        -- 'gemma-4-e4b-it-4bit'
    processed       INTEGER DEFAULT 0,    -- 是否已上推至雲端 (0/1)
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (source_log_id) REFERENCES raw_tracking_logs(id)
);

CREATE INDEX idx_eeb_processed ON edge_event_buffer(processed);
CREATE INDEX idx_eeb_source ON edge_event_buffer(source_log_id);
```

### 7.3 `chat_transcripts` (L1 — 絕不上雲)

```sql
-- [架構文件 §3 T1 明文] 對話逐字稿
CREATE TABLE chat_transcripts (
    id              TEXT PRIMARY KEY,
    thread_id       TEXT NOT NULL,        -- 對話執行緒 ID
    persona_id      TEXT,                 -- 回應的 Persona ID (assistant 時)
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,        -- 對話內容 (L1 明文)
    role_id         TEXT,                 -- 角色情境 ID (M4.3)
    token_count     INTEGER,             -- 估算 token 數
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_ct_thread ON chat_transcripts(thread_id);
CREATE INDEX idx_ct_role_id ON chat_transcripts(role_id);
CREATE INDEX idx_ct_created ON chat_transcripts(created_at);
```

### 7.4 `user_consents` (L1 — 本地隱私同意)

```sql
-- [RISK-11, 架構文件 §3] 使用者隱私同意記錄
CREATE TABLE user_consents (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    consent_type    TEXT NOT NULL,        -- 'voice_cloud', 'social_post_public', ...
    granted         INTEGER NOT NULL,     -- 0 = 拒絕, 1 = 同意
    granted_at      TEXT NOT NULL,
    revoked_at      TEXT,                 -- NULL = 仍有效
    ip_hash         TEXT                  -- 同意時的 IP hash (驗證用)
);

CREATE INDEX idx_uc_user ON user_consents(user_id);
CREATE INDEX idx_uc_type ON user_consents(consent_type);
```

**v1.2 新增 `consent_type` 值**：

| `consent_type`             | 模組       | 說明                                                      |
| -------------------------- | ---------- | --------------------------------------------------------- |
| `voice_cloud`              | M3.4.3.3   | 語音意識流上雲轉錄同意 [RISK-11]                          |
| `social_post_public`       | M3.7       | 社群貼文公開同意 [RISK-12]                                |
| `content_capture_all`      | M1.1 v1.2  | Opt-in 全部軟體內文採集 (`CaptureMode::AllApps`)          |
| `content_capture_selected` | M1.1 v1.2  | Opt-in 指定軟體內文採集，`allowed_processes` 存於 payload |
| `system_notification_mute` | M1.2 v1.1  | 深度工作時靜音系統通知 (`SetNotificationMode`)            |

### 7.5 `raw_content_stores` (L1 — 原始內文附屬表)

```sql
-- [架構文件 §3 T1 明文] 原始內文附屬表，與 raw_tracking_logs 欄位分離以防止側通道洩漏
CREATE TABLE raw_content_stores (
    id              TEXT PRIMARY KEY,     -- 隨機 UUID (作為 raw_tracking_logs payload 中的 content_raw_ref 參照)
    content_raw     TEXT NOT NULL,        -- 擷取之原始網頁/文件明文內容 (上限 4000 字元)
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
```

### 7.6 `role_router_rules` (L1 — 角色路由規則，M4.1.5 自適應更新)

> **v1.2 設計更新**：新增 `persona_id`（UUID，主路由鍵，直接指向 `ai_experts.id`）；`target_domain` 降為選填的人類可讀描述性標籤（由 LLM 自動生成）。此設計讓每個使用者自定義的 Persona 都能作為路由目標，不再受限於系統預設 domain 字串。

```sql
-- [M4.1.5 + RISK-06] 每個 role 獨立規則集，絕不跨 role_id 查詢
-- [v1.2] persona_id 為主路由鍵，target_domain 為可選的人類可讀標籤
CREATE TABLE role_router_rules (
    id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    role_id       TEXT NOT NULL,            -- [RISK-06] 嚴格 role 隔離
    persona_id    TEXT NOT NULL,            -- [v1.2] 直接指向 ai_experts.id（UUID 字串）
                                            -- 取代舊的硬編碼 domain 字串
    pattern       TEXT NOT NULL,            -- regex 字串（中英文均可）
    target_domain TEXT,                     -- [v1.2] 選填，人類可讀標籤
                                            -- e.g. 'math_tutor'（LLM 自動生成）
    confidence    REAL NOT NULL DEFAULT 0.50, -- 規則信心分 [0.0, 1.0]
    source        TEXT NOT NULL DEFAULT 'user_defined',
                                            -- 'user_defined'    : 配對時使用者填寫的 domain_keywords
                                            -- 'llm_correction'  : LLM 驗證後補正
                                            -- 'reflection_title': 從已核准日報任務標題抽取
    status        TEXT NOT NULL DEFAULT 'active',
                                            -- 'active'    : 生效中
                                            -- 'candidate' : 待審查（LLM 提議或自動抽取）
                                            -- 'inactive'  : Persona 被刪除後自動停用
                                            -- 'rejected'  : 精確率不足，廢棄
    hit_count     INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_active   TEXT
);

-- 注意：role_router_rules 存於本地 SQLite（L1），ai_experts 存於雲端 PostgreSQL（L3）
-- 因此無法用 FOREIGN KEY 跨 DB 約束；persona_id 的有效性由應用層保證

CREATE INDEX idx_router_rules_role_status
    ON role_router_rules(role_id, status);
CREATE INDEX idx_router_rules_role_persona
    ON role_router_rules(role_id, persona_id);
```

**欄位說明**：

- `persona_id`：UUID 字串，對應雲端 `ai_experts.id`；應用層在載入規則時驗證 persona 仍為 `is_active = true`
- `target_domain`：選填，供開發者 debug 用；使用者不可見
- `source = 'user_defined'`：配對時使用者填寫的 `domain_keywords` 直接轉為此規則，初始 `status = 'active'`（使用者明確設定，信任度高）
- `status = 'inactive'`：Persona 被軟刪除（`is_active = false`）時，對應規則自動設為 inactive，不等待 REJECT 門檻
- `confidence`：由 `_compute_confidence()` 計算（關鍵字命中 0.60 + 意圖向量 0.25 + 歷史加權 ≤ 0.15）

### 7.7 `routing_samples` (L1 — 路由訓練信號，僅存 hash)

```sql
-- [M4.1.1 + RISK-13] 路由樣本表：只存 SHA-256 hash，絕不存原始訊息明文
CREATE TABLE routing_samples (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    role_id         TEXT NOT NULL,
    user_msg_hash   TEXT NOT NULL,          -- SHA-256(user_msg)，不可還原 [RISK-13]
    keyword_tokens  TEXT,                   -- JSON array，去 PII 後的關鍵詞，供規則提案
    rule_persona_id TEXT,                   -- rule 層決策的 persona_id
    llm_persona_id  TEXT,                   -- LLM 驗證決策（mid/low 信心才有值）
    confidence      REAL,                   -- rule 層的信心分
    outcome         TEXT NOT NULL,
        -- 'rule_high_conf'       : ≥ 0.85 直接採用
        -- 'rule_mid_conf_llm_pending' : 0.50~0.85，背景 LLM 驗證中
        -- 'llm_primary'          : < 0.50，LLM 主導
        -- 'llm_agree'            : LLM 驗證同意 rule 的決定
        -- 'llm_disagree'         : LLM 驗證不同意，觸發候選規則提案
        -- 'user_immediate_rematch' : 使用者路由後立即重新配對（負向信號）
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE INDEX idx_routing_samples_role_outcome
    ON routing_samples(role_id, outcome, created_at);
CREATE INDEX idx_routing_samples_hash
    ON routing_samples(user_msg_hash);    -- 支援去重複查詢
```

**保留策略**：`routing_samples` 保留 30 天，由 M4.1.5 每日排程清除過期記錄（與 `raw_tracking_logs` TTL 一致）。

### 7.8 SQLite 初始化 Pragma  <!-- 原 7.6，因新增 §7.6/7.7 而重新編號 -->

```python
# services/m6_1_sqlite/init.py

async def init_sqlite(db_path: str) -> aiosqlite.Connection:
    """初始化 SQLite 連線並設定必要 Pragma"""
    conn = await aiosqlite.connect(db_path)

    # [M6.1] 效能與並發優化
    await conn.execute("PRAGMA journal_mode=WAL")          # 允許並發讀取
    await conn.execute("PRAGMA synchronous=NORMAL")        # 平衡效能與安全
    await conn.execute("PRAGMA foreign_keys=ON")           # 啟用外鍵約束
    await conn.execute("PRAGMA busy_timeout=5000")         # 等待鎖最多 5s
    await conn.execute("PRAGMA cache_size=-64000")         # 64MB cache

    return conn
```

### 7.9 異常處理

- 資料庫檔案不存在 → Alembic `upgrade head` 自動建立
- Foreign Key 違反 (`edge_event_buffer.source_log_id` 指向不存在的 log) → `IntegrityError`, 拒絕寫入並記錄至 stderr
- 磁碟空間不足 → 在 M0.4 日誌中記錄 `CRITICAL`, 觸發前端 Toast 告知使用者

## 8. Anti-patterns (反模式)

- ❌ **不要在本地 SQLite 中建立任何 L3 業務狀態的資料表** (如 `users`, `ai_experts`)。L3 資料屬雲端 PostgreSQL (M6.2)。
  理由:架構文件 §3 隱私三層分類; 混放會模糊隱私邊界。

- ❌ **不要用 `AUTOINCREMENT` 作為主鍵**。一律使用 UUID (`TEXT PRIMARY KEY`)。
  理由:避免跨裝置合併時的 ID 衝突; 與雲端 PostgreSQL 的 UUID 策略一致。

- ❌ **不要在 `chat_transcripts.content` 欄位上建立全文索引 (FTS)** 除非明確需求且使用者同意。
  理由:FTS 索引會以明文形式展開 token, 增加資料被萃取的風險。

- ❌ **不要跳過 `edge_event_buffer.source_log_id` 的 Foreign Key**。此欄位是 RISK-05 緩解策略的核心,刪除它等於放棄反溯因驗證能力。
  理由:RISK-05 (意圖向量導致圖譜空洞化)。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [x] **`chat_transcripts` 是否需要加密靜態存儲?** (決策：MVP 階段依賴作業系統層級加密 (BitLocker/FileVault) 以及檔案權限管控即可，暫不引入 SQLCipher 以免增加打包與編譯的複雜度。)
- [x] **`edge_event_buffer` 中已上推成功的記錄是否立即刪除?** (決策：保留 7 天，以便在網路不穩或 NSVIF 需要二次驗證時有緩衝，過期後由排程清理。)
- [x] **是否需要 `raw_tracking_logs` 的 TTL 觸發器 (SQLite trigger)?** (決策：由 Python 背景排程 (Cron) 在應用啟動時清理過期日誌即可，不需要寫複雜的 SQLite trigger，降低維護成本。)

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 有 1 個 R06 引用 (差分隱私預留), 已標註主要屬基礎設施
- [x] §3 Schema 用 SQL DDL + Pydantic 描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,有 RISK-05 對應
- [x] §6 測試先於程式碼（含 RISK-13/RISK-06 驗收測試）
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
- [x] v1.2 新增 `role_router_rules`（§7.6）和 `routing_samples`（§7.7）
