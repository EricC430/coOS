# Phase 1.5 Refinement 準備完成報告

**準備日期**：2026-05-31  
**狀態**：✅ 全部就緒  
**預計執行**：2026-06-01 ~ 2026-06-03

---

## 執行摘要

Phase 1（M0.4 + M6.1-M6.5）成功完成後，發現 M6 schema 可進一步精化。已完成合法性評估、RISK 分析、實作計畫與事前檢查清單準備。

**結論**：✅ **建議立即啟動 Phase 1.5 Refinement Sprint**

---

## 核心變動概覽

### 時段卡片層級化（Segment-level）

**前**：每日反思 = 1 個 daily_reflections 表記錄
```
daily_reflections
├─ ai_description: "VS Code 3h Rust"
├─ user_feeling: "有進展"
├─ is_reviewed: true
└─ xp_settled: true (XP 發放單位)
```

**後**：每日反思 = 1 個 parent + N 個 segments
```
daily_reflections (父表)
├─ ai_description: "整日總覽"
├─ is_completed: true (≥1 segment 核准)
└─ total_activity_minutes: 180

daily_reflection_segments (子表，可多個)
├─ [Segment 1] duration_minutes=60, user_feeling="...", is_reviewed=true
├─ [Segment 2] duration_minutes=120, user_feeling=NULL, is_reviewed=false
└─ XP 結算單位：settle_segment_xp() 而非 settle_earned_xp()
```

**收益**：
- XP 發放粒度更細（時段級而非日級）
- 使用者可部分核准，無需一次完成所有反思
- 統計維度擴展：可按專案、AI 專家、時段聚合

---

## 準備成果物

### 1. 合法性評估 ✅

**檔案**：`docs/REFINEMENT_ASSESSMENT_M6.md`

**内容**：
- ✅ 隱私分層檢查：零違反
- ✅ RISK 相容性：RISK-01/07/12 相容或加強
- ✅ 新 RISK 識別：RISK-13（segment 刪除）、RISK-14（lifetime_xp 同步）
- ✅ 上游依賴檢查：零阻擋
- ✅ 優先級排序：緊急（Phase 1.5）vs 次要（Phase 2+）

**簽核結論**：所有變動合法、安全、可執行

---

### 2. 實作計畫 ✅

**檔案**：`docs/PHASE_1_5_REFINEMENT_PLAN.md`

**內容**：

| 日期 | 任務 | 交付物 | 驗收標記 |
|------|------|--------|--------|
| Day 1 (06-01) | M6.4 Segment 子表 + M6.5 settle_segment_xp | Migration × 2 + Tests × 2 (21 個案例) | 全綠 |
| Day 2 (06-02) | M6.2 xp_ledger FK + M6.1 chat_transcripts | Migration × 2 + Tests × 1 (6 個案例) | 全綠 + 統計聚合驗證 |
| Day 3 (06-03) | 集成 + Closure | Closure Report + Git commits | 94+ pass / 0 fail |

**具體產出**：
- 4 個 Alembic migration 檔案（M6.4, M6.5, M6.2 cloud, M6.1 local）
- 3 個新 pytest 檔案（segment approval, segment settlement, ledger stats）
- 4 個 SPEC 版本升級（v1.0 → v1.1）
- Phase 1.5 Closure Report

---

### 3. 事前準備清單 ✅

**檔案**：`docs/PREP_CHECKLIST_PHASE_1_5.md`

**檢查項目**：
- ✅ 文件準備完成（5 份）
- ✅ 環境檢查清單（Supabase, pytest, alembic）
- ✅ 備份策略（pg_dump 教學）
- ✅ Migration 執行步驟（詳細命令）
- ✅ 常見問題 & 解決方案（3 個常見卡點）
- ✅ 最終簽名欄位（待使用者確認）

**Supabase MCP 狀態**：
- ⚠️ 非原生支援，改用 supabase-cli + psql
- ✅ Alembic 遷移框架已就緒（服務層無變）

---

### 4. RISK 審計更新 ✅

**檔案**：`docs/05_integration_risk_audit.md`

**新增 RISK**：

#### RISK-13：Segment 刪除 → 反思無法完成

**失效機制**：已核准 segment A → parent `is_completed = true` → XP 發放 → 後刪除 segment A → parent 失去完成根據

**緩解**：軟刪除 + `is_active` flag + audit log 記錄，不允許自動回滾 XP

**驗收**：segment 軟刪除後 XP 保持，ledger 記錄刪除事實

---

#### RISK-14：Lifetime XP 與 Current XP 同步失敗

**失效機制**：settle 時僅更新 current_xp，忘記 lifetime_xp → 等級計算錯誤

**緩解**：M6.5 所有 XP 異動必須同時更新兩欄（ACID 交易確保）

**驗收**：Gacha 消費 XP 後 lifetime 不減，獲得 XP 時兩欄同增

---

### 5. SPEC 版本更新 ✅

更新標記已添入以下檔案：

- `M6_4_daily_reflections_SPEC.md` v1.0 → v1.1 badge
- `M6_5_acid_gatekeeper_SPEC.md` v1.0 → v1.1 badge （待詳細 DDL）
- `M6_2_postgresql_schemas_SPEC.md` v1.0 → v1.1 badge （待詳細 FK）
- `M6_1_sqlite_schemas_SPEC.md` v1.0 → v1.1 badge （待詳細擴充）

---

## 決策確認矩陣

| 決策項 | 選項 | **選定** | 理由 |
|--------|------|--------|------|
| 時段粒度化 | 保持日級 vs 改時段級 | ✅ 時段級 | 精度↑，統計維度↑，複雜度可控 |
| Parent 表用途 | 保留 vs 重構 | ✅ 重構（父子分離） | 責任明確，統計獨立 |
| Lifetime XP | 不加 vs 加 | ✅ 加 | 防級倒退，遊戲化完整性 |
| Segment FK 約束 | 硬 FK vs 軟（無約束） | ✅ 軟（無約束） | 任務系統未上線，留擴充空間 |
| Segment 刪除策略 | 硬刪 vs 軟刪 | ✅ 軟刪 | RISK-13 緩解，審計追蹤 |

---

## 執行就緒確認

### ✅ 已完成

- [x] 合法性 + RISK 評估（零違反）
- [x] 新 RISK 識別與緩解策略定義
- [x] 3 日詳細實作計畫
- [x] 環境檢查與備份策略
- [x] SPEC 版本標記與內容更新指南
- [x] Git 提交（所有準備文件已入庫）

### ⏳ 待確認（使用者）

- [ ] 是否同意啟動 Phase 1.5 Refinement Sprint（Day 1~3）
- [ ] 預計執行日期確認（建議 2026-06-01~03）
- [ ] 任何對計畫或風險的額外疑問

### ⏳ 待執行（Day 1 開始）

- [ ] 資料庫備份（`pg_dump`）
- [ ] Migration 檔案撰寫（Day 1 早）
- [ ] 測試撰寫與驗證（Day 1~2）
- [ ] 集成驗證（Day 3）

---

## 關鍵時間表

```
2026-05-31 (今天)
└─ Phase 1.5 準備文件完成 + git commit ✅

2026-06-01 (Day 1)
├─ M6.4: daily_reflection_segments 表建立
├─ M6.5: settle_segment_xp() 函數實作
├─ Testing: 21 個驗收標準
└─ 成功標記: segment-level tests all green

2026-06-02 (Day 2)
├─ M6.2: xp_ledger FK + lifetime_xp
├─ M6.1: chat_transcripts 擴充
├─ Testing: 6 個統計聚合測試
└─ 成功標記: ledger FK & stats query OK

2026-06-03 (Day 3)
├─ 全測試跑過 (94+ pass)
├─ Lint 檢查通過
├─ Closure Report 完成
└─ Phase 1.5 正式完成 ✅
```

---

## 後續計畫

### Phase 2 並行（06-04 後）

- M6.3 avatar_url/alias_keywords UI 集成
- M6.1 paralinguistic_metadata 分析（待 M4.2 完成）
- M2.1 Event Dedup & Queue 準備

### Phase 2.5（待 M2.2 完成）

- role_implicit_states Valence-Arousal 情緒維度集成

### Phase 3（待 M4.13 完成）

- segment.task_id 外鍵約束補充

---

## 簽核

**準備工作**：Claude Code (Sonnet 4.6)  
**日期**：2026-05-31  
**狀態**：✅ 完成

**使用者確認**：_________________  
**日期**：_________________

---

## 快速開始指南

若要立即啟動 Phase 1.5：

1. **閱讀**：順序閱讀以下檔案（~30 分鐘）
   - `REFINEMENT_ASSESSMENT_M6.md` — 理解變動的合法性
   - `PHASE_1_5_REFINEMENT_PLAN.md` — 理解 3 日計畫
   - `PREP_CHECKLIST_PHASE_1_5.md` — 執行前最後確認

2. **檢查**：執行 PREP_CHECKLIST 的環境檢查區塊
   ```bash
   # 確認 SUPABASE_DB_URL 有效
   psql "$SUPABASE_DB_URL" -c "SELECT 1;"
   
   # 確認 pytest + ruff 就緒
   pytest --version && ruff --version
   ```

3. **備份**：執行 pg_dump
   ```bash
   pg_dump "$SUPABASE_DB_URL" > ~/coOS_backup_20260531.sql
   ```

4. **簽名**：在本文件或 PREP_CHECKLIST 簽名，表示確認無誤

5. **開始**：Day 1 按 PHASE_1_5_REFINEMENT_PLAN 第一步執行

---

**所有準備文件已就緒。等待你的確認與啟動信號。**
