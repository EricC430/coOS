# Phase 1.5 Refinement — 事前準備清單

**日期**：2026-05-31  
**預計執行日**：2026-06-01 — 2026-06-03  

---

## 1. 文件準備 ✅ 完成

- [x] `REFINEMENT_ASSESSMENT_M6.md` — 合法性評估 + 建議
- [x] `05_integration_risk_audit.md` — 新增 RISK-13, 14
- [x] `PHASE_1_5_REFINEMENT_PLAN.md` — 完整 3 日實作計畫
- [x] SPEC 版本標記（M6.4, M6.5, M6.2, M6.1 → v1.1）

---

## 2. 環境檢查

### 2.1 Supabase MCP 工具狀態

**現況檢查**：
```
☐ Anthropic MCP Registry 中的 Supabase Server
  Status: ⚠️ 未確認在預裝清單內
  備註: Claude Code 目前無原生 Supabase MCP server
  
☐ 替代方案 — supabase-cli + psql
  Status: ✅ 推薦使用
  原因: 直接 SQL + 版本控制整合度更高
```

**建議做法**：
1. **不依賴 MCP Server**，改用 supabase-cli 本地執行
2. Alembic 遷移照常使用（已在 services/alembic_cloud.ini 配置）
3. 若需實時驗證 cloud schema，用 psql 直接查詢

### 2.2 本地工具檢查

```bash
# ✅ Alembic 狀態
$ alembic current -c alembic_cloud.ini
# 應輸出: cloud_20260530_1500 (M6.4 daily_reflections)

# ⏳ Supabase CLI（可選，用於快速驗證）
$ supabase --version
# 若無安裝: brew install supabase-cli (macOS) 或 Windows 等效

# ✅ pytest + ruff
$ pytest --version
$ ruff --version
```

**現況輸出**：
```
pytest: 9.0.3 ✅
ruff: 0.5.0+ ✅
alembic: (已配置) ✅
supabase-cli: (可選) ⏳
```

### 2.3 環境變數確認

```bash
# 檢查 SUPABASE_DB_URL
$ echo $SUPABASE_DB_URL
# 應輸出: postgresql://[user]:[pwd]@[host]:[port]/[db]

# 檢查 .env 檔案
$ cat services/.env | grep -i supabase
```

**建議**：在執行 migration 前確認連線有效
```bash
psql "$SUPABASE_DB_URL" -c "SELECT version();"
```

---

## 3. 資料庫備份策略

### 3.1 備份前檢查清單

- [ ] 確認 Supabase Free tier 允許遠程備份
  - ✅ 允許（但無 Point-in-Time Recovery）
  - 備註：刪除操作無法恢復，遷移需謹慎

- [ ] 確認備份目標位置
  - 本地檔案：`~/coOS_backup_$(date +%Y%m%d_%H%M%S).sql`
  - 大小上限：估計 ~5-10 MB（Phase 1 測試資料）

### 3.2 執行備份命令

**遷移前執行（强烈建議）**：

```bash
# 方法 1：pg_dump（推薦）
SUPABASE_DB_URL="postgresql://..." pg_dump \
  --no-password \
  --schema public \
  --format custom \
  > ~/coOS_backup_$(date +%Y%m%d_%H%M%S).sql

# 驗證備份有效
pg_restore --schema-only ~/coOS_backup_*.sql | head -20

# 方法 2：Supabase CLI（若已安裝）
supabase db pull  # 拉下本地 schema snapshot
```

### 3.3 恢復流程（如需）

```bash
# 若遷移失敗，執行還原
pg_restore --host=... --port=5432 --username=... \
  --dbname=... ~/coOS_backup_*.sql
```

---

## 4. 遷移執行前檢查清單

### 4.1 Alembic 配置驗證

```bash
# 檢查 cloud migration 狀態
$ alembic -c alembic_cloud.ini current
# Expected: cloud_20260530_1500

# 檢查待執行遷移
$ alembic -c alembic_cloud.ini upgrade --sql head
# 應顯示: (no additional upgrades) 或新遷移清單

# 檢查 local migration 狀態
$ alembic current
# Expected: local_20260530_1400
```

### 4.2 SPEC 檔案最終確認

在執行 Day 1 migration 前，確認以下 SPEC 已備好：

- [ ] `M6_4_daily_reflections_SPEC.md` v1.1 — Segment 表 DDL 已寫入 §7.1
- [ ] `M6_5_acid_gatekeeper_SPEC.md` v1.1 — settle_segment_xp() 函數簽名已定
- [ ] `M6_2_postgresql_schemas_SPEC.md` v1.1 — xp_ledger FK 與 lifetime_xp 已定
- [ ] `05_integration_risk_audit.md` — RISK-13, 14 完整記錄

### 4.3 測試框架準備

```bash
# 檢查測試目錄結構
$ ls -la testing/m6_{1,2,3,4,5}/

# 確認 conftest.py 已注入 sys.path
$ grep "sys.path.insert" testing/conftest.py

# 執行 baseline 測試（Phase 1 舊測試應全綠）
$ pytest testing/m6_4 testing/m6_5 -v
# Expected: all pass
```

---

## 5. 遷移執行步驟（簡化版）

### Phase 1.5 Day 1：M6.4 + M6.5

1. **撰寫 migration 檔案**
   ```bash
   # Cloud migration
   alembic revision -c alembic_cloud.ini \
     --message "M6.4 v1.1: add daily_reflection_segments table"
   
   # 編輯生成的 .py 檔案，添加 DDL
   # 見 PHASE_1_5_REFINEMENT_PLAN.md §1.2
   ```

2. **本地驗證（先別 apply）**
   ```bash
   alembic -c alembic_cloud.ini upgrade --sql head > migration_preview.sql
   # 檢查 SQL 是否正確（沒有語法錯誤）
   ```

3. **備份 + 執行遷移**
   ```bash
   # 備份
   pg_dump "$SUPABASE_DB_URL" > backup.sql
   
   # 執行遷移
   alembic -c alembic_cloud.ini upgrade head
   
   # 驗證表已建立
   psql "$SUPABASE_DB_URL" -c "\dt daily_reflection_segments"
   ```

4. **編寫 & 執行測試**
   ```bash
   # 撰寫新測試檔案 testing/m6_4/test_segment_approval.py
   # pytest testing/m6_4 -v
   ```

### Phase 1.5 Day 2：M6.2 + M6.1

同上流程，遷移 xp_ledger FK 與 chat_transcripts 擴充

### Phase 1.5 Day 3：集成 + Closure

```bash
pytest testing/ -q --tb=no --ignore=testing/local_llm
# 應輸出: X pass, 0 fail
```

---

## 6. 常見問題與解決方案

### 問題 1：Alembic 遷移 timeout

**症狀**：`alembic upgrade head` 卡住 >30 秒

**解決**：
```bash
# 檢查連線
psql "$SUPABASE_DB_URL" -c "SELECT 1;" --timeout=5

# 若連線超慢，可能是網路或 Supabase 過載
# 建議用 psql 直接執行 migration SQL 而非 alembic
```

### 問題 2：外鍵衝突 — `violates foreign key constraint`

**症狀**：
```
ERROR: insert or update on table "xp_ledger" violates 
foreign key constraint "xp_ledger_segment_id_fkey"
```

**原因**：新增 FK `segment_id` 但既有 ledger 記錄的 segment_id 為 NULL

**解決**：
```sql
-- 遷移時先添加 FK（可為 NULL）：
ALTER TABLE xp_ledger ADD COLUMN segment_id UUID REFERENCES daily_reflection_segments(id) ON DELETE SET NULL;

-- 若需要，回填邏輯（比對反思 → 段落）
UPDATE xp_ledger SET segment_id = segments.id 
FROM daily_reflection_segments segments
WHERE xp_ledger.reflection_id = segments.reflection_id;
```

### 問題 3：Segment 表建立後，舊 daily_reflections 資料如何處理？

**策略**：
1. **轉移邏輯**（在 migration 中）：
   ```sql
   -- 將舊 daily_reflections 的數據轉入 segments
   INSERT INTO daily_reflection_segments 
     (reflection_id, duration_minutes, ai_description, is_draft, is_reviewed, ...)
   SELECT 
     daily_reflections.id, 
     COALESCE(daily_reflections.activity_minutes, 0),
     daily_reflections.ai_description,
     daily_reflections.is_draft,
     daily_reflections.is_reviewed,
     ...
   FROM daily_reflections;
   ```

2. **驗證**：檢查 segment 計數是否等於反思計數
   ```sql
   SELECT COUNT(*) FROM daily_reflection_segments;
   SELECT COUNT(*) FROM daily_reflections;
   -- 應該相等或略多（多出的是由 segments 直接建立的新卡片）
   ```

---

## 7. 確認清單（執行前必讀）

### 文件層面

- [ ] 已詳讀 `REFINEMENT_ASSESSMENT_M6.md`（理解變動的合法性）
- [ ] 已詳讀 `PHASE_1_5_REFINEMENT_PLAN.md`（理解 3 日計畫）
- [ ] 已詳讀 `05_integration_risk_audit.md` RISK-13, 14（理解新風險與緩解）

### 環境層面

- [ ] SUPABASE_DB_URL 確認有效（`psql ... -c "SELECT 1;"`）
- [ ] pytest + ruff 本地環境就緒
- [ ] Alembic current revision 確認為 `cloud_20260530_1500`
- [ ] 已執行資料庫備份（`pg_dump ... > backup.sql`）

### 代碼層面

- [ ] 已閱讀 M6_SPEC_refinement.md 的 §2.1-2.3（DDL 設計）
- [ ] 已準備 M6.4 migration 檔案框架（等待 DDL 填充）
- [ ] 已準備 M6.5 新函數框架（`settle_segment_xp` 簽名）
- [ ] 已準備測試檔案框架（testing/m6_4/test_segment_approval.py）

### 風險控制層面

- [ ] 已檢視 Phase 1.5 風險清單，理解緩解方案
- [ ] 已確認無 Day 1 ~ Day 3 衝突任務
- [ ] 若有疑問，已記錄在此文件或提出

---

## 8. 執行日期預約

| 日期 | 階段 | 主要任務 | 簽名 |
|------|------|---------|------|
| 2026-06-01 | Day 1 | M6.4 Segment + M6.5 settle_segment | ☐ |
| 2026-06-02 | Day 2 | M6.2 xp_ledger + M6.1 chat_transcripts | ☐ |
| 2026-06-03 | Day 3 | 集成驗證 + Closure Report | ☐ |

---

**確認者簽名**：________________  
**日期**：________________  
**任何疑問或延期理由**：

```
[此處記錄]
```

---

## 附錄：快速參考

### Alembic 常用命令

```bash
# 檢查目前版本
alembic current -c alembic_cloud.ini

# 生成新 migration
alembic revision -c alembic_cloud.ini --message "..."

# 執行升級
alembic upgrade head -c alembic_cloud.ini

# 執行降級（回到上個版本）
alembic downgrade -1 -c alembic_cloud.ini

# 查看 SQL 而不執行
alembic upgrade head --sql -c alembic_cloud.ini > preview.sql
```

### psql 常用命令

```bash
# 連線
psql "$SUPABASE_DB_URL"

# 列出所有表
\dt

# 查看表結構
\d daily_reflection_segments

# 執行 SQL 檔案
psql "$SUPABASE_DB_URL" -f migration.sql

# 計算行數
SELECT COUNT(*) FROM daily_reflections;
```

### Git 常用命令（Phase 1.5）

```bash
# Day 1 commit
git add services/alembic_cloud/versions/...
git commit -m "feat(M6.4, M6.5): Segment-level reflection & XP settlement"

# Day 2 commit
git add services/alembic_cloud/versions/... services/alembic/versions/...
git commit -m "feat(M6.2, M6.1): XP ledger refinement & chat_transcripts"

# Day 3 commit（最後）
git add docs/CLOSURE_REPORT_PHASE_1_5.md
git commit -m "docs(phase1_5): Phase 1.5 closure report — all tests pass"
```
