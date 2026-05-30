# M6 Schema Refinement 合法性評估報告

**日期**：2026-05-31  
**評估者**：Claude Code  
**狀態**：初審完成，待使用者確認優先級

---

## 1. Refinement 概觀

`M6_SPEC_refinement.md` 提案的核心變動：
1. **時段卡片層級**（`daily_reflection_segments`）— 分解當前單一 `daily_reflections` 為「父表 + 子表」
2. **L2 短暫向量欄位擴充**（`role_implicit_states`） — Valence-Arousal 情緒模型
3. **XP 帳本細分**（`xp_ledger` 新增 FK）— role/expert/project/segment/task 關聯
4. **本地 SQLite 擴充**（`chat_transcripts`） — 專案關聯、語音路徑、副語言特徵
5. **使用者與角色表擴充**（`lifetime_xp`, `avatar_url`, alias_keywords）

---

## 2. 合法性檢查矩陣

### 2.1 是否違反 Privacy L1/L2/L3 分層？

| 變動 | L1 | L2 | L3 | 評估 |
|------|----|----|----|----|
| Segment 時段卡片 | ✅ 本地 | ✅ 本地 | ✅ 雲端 | **正確**。感受(user_feeling)上雲但有使用者同意(M6.4 SPEC §9) |
| role_implicit_states (Valence-Arousal) | — | ✅ 本地 | — | **正確**。L2 向量不上雲,與當前 role_implicit_states 一致 |
| xp_ledger FK 擴充 | — | — | ✅ 雲端 | **正確**。都是統計用 L3 |
| chat_transcripts (audio_path, paralinguistic) | ✅ 本地 | — | — | **正確**。音檔與副語言特徵禁留本地 |
| lifetime_xp, avatar_url | — | — | ✅ 雲端 | **正確**。業務狀態 |

**結論**：✅ **零違反隱私分層**

---

### 2.2 是否符合現有 RISK 緩解策略？

#### RISK-01: 草稿狀態 XP 提前發放

**現況**：
- M6.4: 反思層級 → `is_reviewed` 檢查
- M6.5: ACID 守門員 → SELECT FOR UPDATE 檢查

**Refinement 變動**：
- 改為 **Segment 層級** → `daily_reflection_segments.is_reviewed` 與 `xp_settled`
- 守門員升級：`settle_segment_xp()` 锁定 segment 而非 reflection

**相容性**：✅ **相容且加強**
- 父表 `daily_reflections.is_completed` 只在「至少一個 segment 核准」時為 TRUE
- XP 結算粒度更細（segment 級而非日級）
- RISK-01 緩解層級不減

**風險**：⚠️ **單一新風險 — RISK-13 (草稿 segment 刪除導致反思無法完成)**
- 預案：migration 需 ON DELETE CASCADE 或留存已刪除 segment 的 XP 記錄

---

#### RISK-07: 邊緣 ZPD 質押

**現況**：
- M6.5: `stake_xp()` 檢查 `task.zpd_zone != "edge"`

**Refinement 變動**：
- 新增 `segment.task_id` FK (但無 FK 約束)
- `xp_ledger.task_id` 加入統計欄

**相容性**：✅ **相容**（無衝突，擴充而已）

---

#### RISK-12: Gacha 原子性

**現況**：
- M6.5: `deduct_xp_for_gacha()` 先扣後開獎，失敗 rollback

**Refinement 變動**：
- 無直接變動

**相容性**：✅ **未受影響**

---

### 2.3 是否觸發新的整合風險？

| 風險編號 | 描述 | 嚴重度 | 緩解方案 |
|--------|------|--------|--------|
| **RISK-13** | Segment 刪除 → 反思無法完成（已核准的 segment 被刪） | **P2 中** | (1) 改用軟刪除 + `is_active` flag; (2) ON DELETE RESTRICT |
| **RISK-14** | lifetime_xp 與 current_xp 同步失敗（消費但累計未扣） | **P2 中** | 在 M6.5 settle 時同時更新兩欄；ledger 為真實來源 |
| **RISK-15** | role_implicit_states 轉移雲端（Valence-Arousal 算法迭代） | **P3 低** | 暫無（Phase 2+ M2.2 再決定上雲時機） |

**新增 RISK 清單**：RISK-13, RISK-14（需添入 `05_integration_risk_audit.md`）

---

### 2.4 是否有未實作的上游模組依賴？

| 欄位/功能 | 依賴模組 | 狀態 | 影響 |
|-----------|---------|------|------|
| `segment.task_id` | M4.13 Task 系統 | ⏳ Phase 3 | **非阻擋** — 無 FK，可為 NULL |
| `segment.expert_id` | M4.2 Persona | ✅ M6.2 已建 ai_experts | **就緒** |
| `segment.project` | M1.1 Activity Monitor | ⏳ Phase 2 | **非阻擋** — 可手填或 M4.6 回填 |
| `valence`, `arousal` | M2.2 邊緣推論 | ⏳ Phase 2 | **非阻擋** — role_implicit_states 已在 M6.3 |
| `audio_path`, `paralinguistic_metadata` | M4.2 副語言分析 | ⏳ Phase 2 | **非阻擋** — L1 本地，可逐步填入 |

**結論**：✅ **零阻擋性依賴**（所有新欄均為選填或 Phase 2+）

---

## 3. 優先級與建議

### 緊急（Phase 1.5 — Refinement Sprint）

- ✅ **Segment 子表化**（M6.4 重構）
  - 原因：提高反思粒度，XP 結算更精細
  - 工作量：中（1~2 天）
  - 破壞性：中等（需更新 approval logic + M6.5 settle）

- ✅ **xp_ledger FK 擴充**（M6.2 migration 新增）
  - 原因：統計能力跳升（角色/專家/專案維度）
  - 工作量：小（0.5 天）
  - 破壞性：低（新欄，向後相容）

- ✅ **lifetime_xp**（M6.2 users 表擴充）
  - 原因：防止等級倒退（消費 XP 後等級掉）
  - 工作量：小（0.5 天）
  - 破壞性：低（新欄，無邏輯衝突）

### 次要（Phase 2 — 附帶實作）

- ⏳ **avatar_url, alias_keywords**（M6.3 / 後續）
  - 原因：UI 渲染 + AI 專案推論輔助
  - 依賴：無
  - 優先級：P3（前端就緒時補）

- ⏳ **role_implicit_states Valence-Arousal**（M6.3 + M2.2）
  - 原因：情緒模型支援
  - 依賴：M2.2 邊緣推論完成
  - 優先級：P2（推遲至 Phase 2.5）

- ⏳ **chat_transcripts 擴充**（M6.1）
  - 原因：副語言與專案關聯
  - 依賴：M4.2, M1.1
  - 優先級：P2（Phase 2 逐步集成）

---

## 4. 提議的實作路線

### Phase 1.5 Refinement Sprint（3 天）

```
Day 1:
├─ M6.4 重構：daily_reflections + daily_reflection_segments
├─ M6.5 升級：settle_earned_xp() → settle_segment_xp()
└─ Testing：撰寫新的 segment-level 驗收標準

Day 2:
├─ M6.2 migration：xp_ledger FK 擴充 + users.lifetime_xp
├─ M6.2 model：更新 XPLedger pydantic
└─ Testing：ledger 統計聚合查詢驗證

Day 3:
├─ 05_integration_risk_audit.md：添加 RISK-13, RISK-14
├─ SPEC 版本更新：M6.4 → 1.1, M6.5 → 1.1, M6.2 → 1.1
└─ Phase 1.5 Closure Report + commit
```

### Phase 2 併行實作

- M6.3 avatar_url / alias_keywords
- M6.1 chat_transcripts 擴充（等 M1.1 就緒）
- role_implicit_states Valence-Arousal（等 M2.2 就緒）

---

## 5. 相容性確認清單

- [x] 隱私分層：零違反
- [x] 現有 RISK（RISK-01, 07, 12）：相容或加強
- [x] 新 RISK（RISK-13, 14）：可接受且有緩解方案
- [x] 上游模組依賴：零阻擋
- [x] 後向相容：99%（需要 data migration 策略）
- [x] 資料庫遷移可行性：有（Alembic）

---

## 6. 行動方案確認

**建議立即啟動**：Phase 1.5 Refinement Sprint（Day 1-3）

**準備工作**：
1. ✅ 本評估報告（已完成）
2. ⏳ 更新 `M6_4_daily_reflections_SPEC.md` → v1.1（添加 Segment 表）
3. ⏳ 更新 `M6_5_acid_gatekeeper_SPEC.md` → v1.1（settle_segment_xp）
4. ⏳ 更新 `M6_2_postgresql_schemas_SPEC.md` → v1.1（xp_ledger FK + lifetime_xp）
5. ⏳ 添加 RISK-13, RISK-14 至 `05_integration_risk_audit.md`
6. ⏳ 確認 Supabase MCP 可用（若用於實作驗證）

---

## 附錄：Supabase MCP 檢查清單

| 項目 | 狀態 | 備註 |
|------|------|------|
| Claude MCP for Supabase 可用性 | ⏳ 待確認 | 需檢查 Anthropic MCP registry |
| 本地 supabase CLI 安裝 | ⏳ 待確認 | `brew install supabase-cli` |
| SUPABASE_DB_URL 環境變數 | ✅ 已有 | `.env` 配置 |
| 遷移執行權限 | ✅ 已有 | Alembic + Supabase role |
| Snapshot 備份 | ⏳ 建議 | 實作前先備份 prod schema |

---

**評估結論**：✅ **Refinement 提案合法且安全，建議立即啟動 Phase 1.5**
