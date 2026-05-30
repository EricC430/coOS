# Phase 1.5 Refinement Sprint — 完整實作計畫

**版本**：v1.0-draft  
**日期**：2026-05-31  
**預計工期**：3 天（Day 1-3）  
**後續階段**：Phase 2 integration

---

## 0. 背景與決策

自 Phase 1 完成後，發現 M6 schema 可進一步精化以支援：
1. **Segment 層級 XP 結算**（粒度提升：日 → 時段）
2. **XP 帳本細分統計**（維度擴展：role/expert/project/segment/task）
3. **生涯累計與可用餘額分離**（防級倒退）
4. **角色與專案的 AI 自動發現**（支援未來 M2.2 推論）

**合法性驗證**：✅ 見 `REFINEMENT_ASSESSMENT_M6.md`
- 隱私分層：零違反
- 現有 RISK（01, 07, 12）：相容或加強
- 新 RISK（13, 14）：已添入 `05_integration_risk_audit.md`
- 上游依賴：零阻擋

---

## 1. SPEC 更新計畫

### 1.1 M6.4 Daily Reflections (v1.0 → v1.1)

**變動內容**：

| 項目 | v1.0 | v1.1 | 作用 |
|------|------|------|------|
| 主要表 | `daily_reflections` (單表) | `daily_reflections` (父表) + `daily_reflection_segments` (子表) | 分離日統計與時段粒度 |
| 核准單位 | 日級 (`is_reviewed` on parent) | 時段級 (`is_reviewed` on segment) | XP 結算更精細 |
| 狀態標誌 | `is_draft`, `is_reviewed` | 同+`is_completed` on parent | 完成條件：≥1 segment 核准 |
| 新增指標 | 無 | `focus_depth`, `distraction_count`, `reflection_word_count`, `reflection_edit_seconds`, `is_aligned`, `scaffold_prompt` | 行為與投入度追蹤 |
| 新增欄位 (parent) | `activity_minutes` | `total_activity_minutes`, `overall_mood_score`, `streak_multiplier`, `completed_at` | 日統計與遊戲化 |

**SPEC 檔案**：`docs/modules/M6_4_daily_reflections_SPEC.md` (v1.0 → v1.1)

**具體寫法**（§7.1 Implementation Notes）：
```sql
-- 新增子表
CREATE TABLE daily_reflection_segments (
    id UUID PRIMARY KEY,
    reflection_id UUID NOT NULL,
    -- 行為指標
    duration_minutes INT DEFAULT 0,
    focus_depth REAL DEFAULT 1.0,
    distraction_count INT DEFAULT 0,
    -- 使用者反思 (核准時必填)
    user_feeling TEXT,
    user_action_plan TEXT,
    is_draft BOOLEAN DEFAULT TRUE,
    is_reviewed BOOLEAN DEFAULT FALSE,
    -- XP 結算狀態
    earned_xp INT DEFAULT 0,
    xp_settled BOOLEAN DEFAULT FALSE,
    -- ... 其他欄位見 M6_SPEC_refinement.md §2.1
    FOREIGN KEY (reflection_id) REFERENCES daily_reflections(id) ON DELETE CASCADE
);

-- 修改父表
ALTER TABLE daily_reflections ADD COLUMN is_completed BOOLEAN DEFAULT FALSE;
ALTER TABLE daily_reflections ADD COLUMN completed_at TIMESTAMPTZ;
ALTER TABLE daily_reflections ADD COLUMN total_activity_minutes INT DEFAULT 0;
ALTER TABLE daily_reflections ADD COLUMN overall_mood_score INT;
ALTER TABLE daily_reflections ADD COLUMN streak_multiplier REAL DEFAULT 1.0;
```

**驗收標準更新**（§6）：
```python
# AC-1: Segment 核准需填寫 user_feeling + user_action_plan
# AC-2: 日反思「至少一個 segment 核准」才標記 is_completed
# AC-3: parent is_completed 為 TRUE 時，updated_at 與 completed_at 更新
```

---

### 1.2 M6.5 ACID Gatekeeper (v1.0 → v1.1)

**變動內容**：

| 項目 | v1.0 | v1.1 | 作用 |
|------|------|------|------|
| 結算單位 | `settle_earned_xp(reflection_id)` | `settle_segment_xp(segment_id)` | 時段級粒度 |
| SELECT FOR UPDATE | 鎖 `daily_reflections` | 鎖 `daily_reflection_segments` | 更精準的鎖定 |
| 欄位更新 | 無 | 新增 `lifetime_xp` 同步更新（RISK-14 緩解） | 防級倒退 |
| 守門檢查 | `reflection.is_reviewed` | `segment.is_reviewed` | 檢查粒度一致化 |

**SPEC 檔案**：`docs/modules/M6_5_acid_gatekeeper_SPEC.md` (v1.0 → v1.1)

**具體寫法**（§7.1 核心交易函式）：
```python
async def settle_segment_xp(
    self, segment_id: str, user_id: str, amount: int
) -> TransactionResult:
    """[RISK-01, RISK-14] Segment 級別 XP 結算（含 lifetime_xp 更新）"""
    async with self._session.begin():
        # 1. SELECT FOR UPDATE 鎖定 segment
        segment = await self._session.execute(
            select(DailyReflectionSegment)
            .where(DailyReflectionSegment.id == segment_id)
            .with_for_update()
        )
        segment = segment.scalar_one_or_none()
        
        # 2. 守門檢查 (RISK-01)
        if segment.is_draft or not segment.is_reviewed:
            return TransactionResult(False, "GATEKEEPER_001", "segment_not_approved")
        if segment.xp_settled:
            return TransactionResult(False, "GATEKEEPER_002", "already_settled")
        
        # 3. 同時更新 current_xp 與 lifetime_xp (RISK-14 緩解)
        user = await self._session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user.scalar_one()
        user.current_xp += amount
        user.lifetime_xp += amount
        
        # 4. 寫入 ledger （見 §2.3）
        ledger = XPLedger(...)
        self._session.add(ledger)
        
        # 5. 標記結算
        segment.xp_settled = True
        segment.earned_xp = amount
        
        return TransactionResult(True)
```

**驗收標準更新**：
```python
# AC-1: SELECT FOR UPDATE 鎖定 segment（not reflection）
# AC-2: lifetime_xp += amount（RISK-14 驗證）
# AC-3: Gacha 與 Stake 邏輯無變（兼容向後）
```

---

### 1.3 M6.2 PostgreSQL Schemas (v1.0 → v1.1)

**變動內容**：

| 項目 | v1.0 | v1.1 | 作用 |
|------|------|------|------|
| `users` 表 | `current_xp` | `current_xp` + `lifetime_xp` | 防級倒退 (RISK-14) |
| `roles` 表 | `display_name`, ... | 新增 `avatar_url` | UI 頭像渲染 |
| `xp_ledger` 表 | `user_id`, `amount`, `xp_type`, ... | 新增 FK: `role_id`, `expert_id`, `project`, `segment_id`, `task_id` | 統計維度擴展 |
| `role_projects` 表 | 無 | 新增 `inferred_by_ai`, `alias_keywords` | AI 自動發現支援 |
| `role_settings` 表 | 基礎欄 | 新增 `weekly_target_minutes` | 專注目標管理 |
| `role_implicit_states` 表 | `label`, `confidence` | 新增 `valence`, `arousal`, `raw_triggers` | Valence-Arousal 情緒模型 |

**SPEC 檔案**：`docs/modules/M6_2_postgresql_schemas_SPEC.md` (v1.0 → v1.1)

**具體寫法**（新增 migration）：
```python
# services/alembic_cloud/versions/20260531_1600_m6_2_refinement_xp_ledger.py

def upgrade() -> None:
    # users 表擴充
    op.add_column('users', sa.Column('lifetime_xp', sa.Integer(), server_default='0'))
    
    # roles 表擴充
    op.add_column('roles', sa.Column('avatar_url', sa.VARCHAR(512), nullable=True))
    
    # xp_ledger 表擴充 (新增 FK)
    op.add_column('xp_ledger', sa.Column('role_id', sa.UUID(), nullable=True))
    op.add_column('xp_ledger', sa.Column('expert_id', sa.UUID(), nullable=True))
    op.add_column('xp_ledger', sa.Column('project', sa.Text(), nullable=True))
    op.add_column('xp_ledger', sa.Column('segment_id', sa.UUID(), nullable=True))
    op.add_column('xp_ledger', sa.Column('task_id', sa.UUID(), nullable=True))
    
    # role_projects 表擴充
    op.add_column('role_projects', sa.Column('inferred_by_ai', sa.Boolean(), server_default='FALSE'))
    op.add_column('role_projects', sa.Column('alias_keywords', sa.Text(), nullable=True))
    
    # role_settings 表擴充
    op.add_column('role_settings', sa.Column('weekly_target_minutes', sa.Integer(), server_default='0'))
    
    # role_implicit_states 表擴充
    op.add_column('role_implicit_states', sa.Column('valence', sa.Float(), nullable=True))
    op.add_column('role_implicit_states', sa.Column('arousal', sa.Float(), nullable=True))
    op.add_column('role_implicit_states', sa.Column('raw_triggers', sa.Text(), nullable=True))
```

---

### 1.4 M6.1 SQLite Schemas (v1.0 → v1.1)

**變動內容**：

| 項目 | v1.0 | v1.1 | 作用 |
|------|------|------|------|
| `chat_transcripts` 表 | 基礎欄 | 新增 `project`, `audio_path`, `paralinguistic_metadata` | 專案關聯、語音分析 |

**SPEC 檔案**：`docs/modules/M6_1_sqlite_schemas_SPEC.md` (v1.0 → v1.1)

```python
# services/alembic/versions/20260531_1600_m6_1_refinement_chat_transcripts.py

def upgrade() -> None:
    op.add_column('chat_transcripts', sa.Column('project', sa.Text(), nullable=True))
    op.add_column('chat_transcripts', sa.Column('audio_path', sa.Text(), nullable=True))
    op.add_column('chat_transcripts', sa.Column('paralinguistic_metadata', sa.Text(), nullable=True))
```

---

### 1.5 M6.3 Role Context Tables (v1.0 → v1.1)

**變動內容**：無新增表，只有擴充 `role_implicit_states` 與 `role_projects`（同 M6.2 + M6.1）

---

## 2. RISK 更新

### 新增 RISK-13 與 RISK-14

已於 `05_integration_risk_audit.md` 添加完整的四欄（觸發/失效/緩解/驗收）。

**修改位置**：`docs/05_integration_risk_audit.md` (已更新)

---

## 3. 實作路線圖

### Day 1：M6.4 + M6.5 核心重構

**任務**：
1. ✅ 讀 M6_SPEC_refinement.md §2.1-2.3（Segment 表設計）
2. ⏳ 撰寫 M6.4 migration：創建 `daily_reflection_segments` 表 + 修改 `daily_reflections`
3. ⏳ 撰寫 `services/m6_4_daily_reflections/approve.py`：
   - 新增 `approve_daily_reflection_flow()` 函數（驗證「≥1 segment 核准」）
   - 舊函數標記為 deprecated
4. ⏳ 升級 M6.5 gatekeeper：`settle_segment_xp()` 替代 `settle_earned_xp()`
5. ⏳ 編寫 segment 級別測試（testing/m6_4/ 與 testing/m6_5/）

**預計輸出**：
- `services/alembic_cloud/versions/20260531_*_m6_4_segments.py`
- `services/m6_4_daily_reflections/approve.py` (新增 `approve_daily_reflection_flow`)
- `services/m6_5_acid_gatekeeper/gatekeeper.py` (新增 `settle_segment_xp`)
- `testing/m6_4/test_segment_approval.py` (13 個新驗收標準)
- `testing/m6_5/test_segment_settlement.py` (8 個新驗收標準)

**成功標記**：所有 segment 級別測試通過，parent `is_completed` 邏輯正確

---

### Day 2：M6.2 + M6.1 + M6.3 擴充

**任務**：
1. ⏳ 撰寫 M6.2 migration：`lifetime_xp`, `avatar_url`, xp_ledger FK 擴充
2. ⏳ 撰寫 M6.1 migration：`chat_transcripts` 擴充
3. ⏳ 更新 Pydantic models：
   - `services/m6_2_postgresql/models.py`: `User.lifetime_xp`, `XPLedger` FK 欄
   - `services/m6_1_sqlite/models.py`: `ChatTranscript` 擴充
4. ⏳ 編寫 lifetime_xp 與 xp_ledger 統計查詢驗證測試

**預計輸出**：
- `services/alembic_cloud/versions/20260531_*_m6_2_xp_ledger_refinement.py`
- `services/alembic/versions/20260531_*_m6_1_chat_refinement.py`
- `services/m6_2_postgresql/models.py` (更新 User, XPLedger)
- `services/m6_1_sqlite/models.py` (更新 ChatTranscript)
- `testing/m6_2/test_xp_ledger_statistics.py` (6 個 ledger 聚合查詢測試)

**成功標記**：ledger FK 寫入正確，統計聚合查詢返回正確結果

---

### Day 3：集成驗證 + Closure

**任務**：
1. ⏳ 跑全測試套（pytest testing/ -q）→ 確認無回歸
2. ⏳ Lint 檢查（ruff check . --fix）
3. ⏳ 更新版本號：
   - M6.4 SPEC v1.0 → v1.1
   - M6.5 SPEC v1.0 → v1.1
   - M6.2 SPEC v1.0 → v1.1
   - M6.1 SPEC v1.0 → v1.1
4. ⏳ 生成 Phase 1.5 Closure Report
5. ⏳ 合併所有變動 → git commit

**預計輸出**：
- `docs/CLOSURE_REPORT_PHASE_1_5.md`
- 6 個 git commits（每天分組 commit，或最後合併為 3 個大 commit）
- 全測試通過報告

**成功標記**：94+ pass / 0 fail / Phase 1.5 正式完成

---

## 4. 事前準備清單

### 4.1 Supabase MCP 驗證

- [ ] 檢查 Anthropic MCP registry 中是否有 `supabase` server
  ```bash
  # 或查閱 https://github.com/Anthropic/anthropic-sdk-python/tree/main/examples/mcp_servers
  ```
- [ ] 若有，確認支援的操作（列表、讀、寫、執行 SQL）
- [ ] 若無，改用 `supabase-cli` + psql 直接操作

### 4.2 本地環境檢查

```bash
# 檢查 alembic 狀態
alembic current -c alembic_cloud.ini  # 目前最新 revision

# 檢查 SUPABASE_DB_URL
echo $SUPABASE_DB_URL

# 備份現有 schema（可選，但強烈建議）
pg_dump "$SUPABASE_DB_URL" > backup_20260531.sql
```

### 4.3 文件準備完成

- [x] `REFINEMENT_ASSESSMENT_M6.md` 合法性評估
- [x] `05_integration_risk_audit.md` 新增 RISK-13, 14
- [x] `PHASE_1_5_REFINEMENT_PLAN.md` 本文件
- [ ] 各 SPEC 版本更新（v1.0 → v1.1）— 待完成

---

## 5. 風險與緩解

| 風險 | 嚴重度 | 緩解 |
|------|--------|------|
| Segment 表遷移失敗 → 資料丟失 | P1 嚴重 | (1) 遷移前備份 (2) 遷移使用 transaction (3) 逐步 apply |
| `lifetime_xp` 同步失敗 → 等級計算錯 | P2 中 | (1) ACID 交易確保同步 (2) audit log 記錄 (3) 驗收測試覆蓋 |
| Segment 刪除導致反思無法完成 | P2 中 | (1) 軟刪除 + `is_active` flag (2) RESTRICT FK |
| 新 FK 外鍵衝突 → 遷移 hang | P2 中 | (1) 逐欄新增（非一次全加）(2) 手工驗證 referential integrity |

---

## 6. 後續階段（Phase 2+）

- **Phase 2 並行**：M6.3 avatar_url/alias_keywords UI 集成，M6.1 paralinguistic 分析（待 M4.2 完成）
- **Phase 2.5**：role_implicit_states Valence-Arousal（待 M2.2 邊緣推論完成）
- **Phase 3**：segment.task_id 外鍵添加（待 M4.13 Task 系統上線）

---

## 確認清單

**在執行 Day 1 前，請確認**：

- [ ] 已讀此計畫文件（PHASE_1_5_REFINEMENT_PLAN.md）
- [ ] 已讀評估報告（REFINEMENT_ASSESSMENT_M6.md）
- [ ] 已讀新增 RISK（05_integration_risk_audit.md RISK-13, 14）
- [ ] Supabase 環境變數確認無誤
- [ ] 已備份 Supabase 現有 schema（建議）
- [ ] pytest + ruff 本地環境就緒

---

**核准簽名**：_________________  
**日期**：2026-05-31
