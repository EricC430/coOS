# Phase 1.5 Closure Report

**Phase**: 1.5 Refinement Sprint  
**Status**: CLOSED  
**Period**: 2026-05-31  
**Author**: EricC430 + Claude Sonnet 4.6

---

## 1. 執行摘要

Phase 1.5 為 M6 schema 的精化衝刺，將 XP 結算粒度從「日」提升至「時段（segment）」，並完成資安補強（RLS）與 Pydantic 模型的完整覆蓋。原計畫 3 天，實際於 1 天內完成全部實作並通過 migration 驗收。

**最終測試結果：121 pass / 6 skip / 0 fail**

---

## 2. 完成項目清單

### 2.1 Day 1 — M6.4 + M6.5 核心重構

#### M6.4 Daily Reflections v1.0 → v1.1

| 項目 | 狀態 | 說明 |
|------|------|------|
| Cloud migration `20260531_1000` | ✅ Applied | CREATE `daily_reflection_segments` + ALTER `daily_reflections` |
| `daily_reflection_segments` 子表 | ✅ | XP 結算單位：`is_draft`, `is_reviewed`, `user_feeling`, `user_action_plan`, `is_active` (soft-delete) |
| `daily_reflections` 父表精化 | ✅ | 移除草稿欄 → 加 `is_completed`, `completed_at`, `total_activity_minutes`, `streak_multiplier` |
| `approve.py` 完整重寫 | ✅ | `approve_daily_reflection_flow()` 批次 segment 核准，v1.0 backward-compat preserved |
| `can_grant_segment_xp()` | ✅ | [RISK-01] 段落級 XP 守門謂詞 |
| 測試 `test_segment_approval.py` | ✅ | 11 個 AC 全通過 |

**研究依據**: [R08 §四.2] 微摩擦力（both fields or neither）; [R08 §六.1] IKEA 效應

#### M6.5 ACID Gatekeeper v1.0 → v1.1

| 項目 | 狀態 | 說明 |
|------|------|------|
| `settle_segment_xp()` | ✅ | 新主 API：鎖定 segment 而非父反思，含 RISK-01/13/14 全守門 |
| `lifetime_xp` 同步遞增 | ✅ | [RISK-14] earn 路徑同步 current_xp + lifetime_xp |
| Gacha/Stake 不觸碰 lifetime_xp | ✅ | [RISK-14] spend 路徑僅減 current_xp |
| Ledger `segment_id` FK | ✅ | 支援統計維度查詢 |
| 測試 `test_segment_settlement.py` | ✅ | 9 個 AC + 2 個 RISK-14 invariant 全通過 |

---

### 2.2 Day 2 — M6.2 + M6.1 擴充

#### M6.2 PostgreSQL Schemas v1.0 → v1.1

| 項目 | 狀態 | 說明 |
|------|------|------|
| Cloud migration `20260531_1100` | ✅ Applied | users.lifetime_xp, roles.avatar_url, xp_ledger FK 擴充 |
| `users.lifetime_xp` | ✅ | [RISK-14] `server_default=0`, 唯增不減 |
| `roles.avatar_url` | ✅ | UI 頭像渲染支援 |
| `xp_ledger` FK: expert_id/project/segment_id/task_id | ✅ | 統計維度擴展（role_id 已存在於 v1.0） |
| `role_projects`: inferred_by_ai + alias_keywords | ✅ | AI 自動發現欄位 |
| `role_settings`: weekly_target_minutes | ✅ | 專注時長目標 |
| Pydantic models `m6_2_postgresql/models.py` | ✅ NEW | 完整 v1.1 L3 schema 模型覆蓋 |

#### M6.1 SQLite Schemas v1.0 → v1.1

| 項目 | 狀態 | 說明 |
|------|------|------|
| Local migration `20260531_1000` | ✅ Applied | `chat_transcripts` 加 project/audio_path/paralinguistic_metadata |
| `chat_transcripts.audio_path` | ✅ | [L1 local-only] 語音附件路徑，永不上雲 |
| `chat_transcripts.paralinguistic_metadata` | ✅ | JSON：tempo/pitch/stress，M4.2 語調狀態機輸入 |
| Pydantic models `m6_1_sqlite/models.py` | ✅ NEW | 完整 v1.1 L1/L2 schema 模型覆蓋 |

---

### 2.3 Phase 2+ 補強項目（同步完成）

#### RLS Row Level Security

| 表 | 策略 | 隔離依據 |
|-----|------|---------|
| `users` | `users_self_only` | `id = auth.uid()` |
| `roles` | `roles_owner` | `user_id = auth.uid()` |
| `ai_experts` | `ai_experts_owner` | JOIN `roles.user_id` |
| `xp_ledger` | `xp_ledger_owner` | `user_id = auth.uid()` |
| `badge_definitions` | `badge_definitions_public_read` | public SELECT only |
| `user_badges` | `user_badges_owner` | `user_id = auth.uid()` |
| `role_projects` | `role_projects_owner` | JOIN `roles.user_id` |
| `role_settings` | `role_settings_owner` | JOIN `roles.user_id` |
| `daily_reflections` | `daily_reflections_owner` | `user_id = auth.uid()` |
| `daily_reflection_segments` | `daily_reflection_segments_owner` | JOIN `daily_reflections.user_id` |

Migration `cloud_20260531_1200` 已 applied。

#### role_implicit_states Valence-Arousal（本地）

Local migration `20260531_1200` 加入：
- `valence REAL` — [-1.0, 1.0] (sad → happy)
- `arousal REAL` — [-1.0, 1.0] (calm → excited)
- `raw_triggers TEXT` — JSON 陣列，觸發情緒的遙測事件清單

[R03 §6] Valence-Arousal circumplex model，為 Phase 2.5 M2.2 邊緣推論前置。

---

## 3. Migration 紀錄

### Cloud (Supabase PostgreSQL)

| Revision | 名稱 | 狀態 |
|----------|------|------|
| `cloud_20260530_1300` | M6.2 cloud schemas | ✅ |
| `cloud_20260530_1400` | M6.3 role_projects + role_settings | ✅ |
| `cloud_20260530_1500` | M6.4 daily_reflections | ✅ |
| `cloud_20260531_1000` | M6.4 v1.1 segment sub-table | ✅ |
| `cloud_20260531_1100` | M6.2 v1.1 ledger + lifetime_xp | ✅ |
| `cloud_20260531_1200` | RLS — all tables | ✅ |

Current head: `cloud_20260531_1200`

### Local (SQLite)

| Revision | 名稱 | 狀態 |
|----------|------|------|
| `20260530_1200` | initial | ✅ |
| `20260530_1300` | M6.1 SQLite schemas | ✅ |
| `20260530_1400` | M6.3 role_implicit_states | ✅ |
| `20260531_1000` | M6.1 v1.1 chat_transcripts | ✅ |
| `20260531_1200` | M6.3 v1.1 Valence-Arousal | ✅ |

Current head: `20260531_1200`

---

## 4. 測試覆蓋

| 測試檔案 | 通過數 | 核心驗收標準 |
|---------|-------|------------|
| `testing/m6_4/test_segment_approval.py` | 11/11 | AC-1~11 segment 級核准流程 |
| `testing/m6_5/test_segment_settlement.py` | 9/9 | RISK-01/13/14 settlement 守門 |
| `testing/m6_5/test_xp_gatekeeper.py` | 7/7 | 原有 Gacha/Stake 不回歸 |
| `testing/m6_4/test_daily_reflections.py` | 14/14 | v1.1 API + migration audit |
| `testing/m6_2/test_xp_ledger.py` | 6/6 | cloud skipped (DB required) |
| 其他既有測試 | 74/74 | 無回歸 |
| **總計** | **121 pass / 6 skip / 0 fail** | |

---

## 5. RISK 緩解記錄

| RISK ID | 名稱 | 緩解措施 | 驗收 |
|---------|------|---------|------|
| RISK-01 | XP 守門（未審核不得結算） | `can_grant_segment_xp()` + `settle_segment_xp()` 雙層檢查 | ✅ test_xp_blocked_for_draft_segment |
| RISK-13 | Soft-delete（已核准 segment 不可硬刪） | `is_active` flag + 審核前必檢查 | ✅ test_soft_deleted_segment_blocked |
| RISK-14 | 等級倒退（花費 XP 不能降級） | `lifetime_xp` 唯增不減；earn 同步兩欄，spend 只減 `current_xp` | ✅ test_lifetime_xp_not_decremented_by_gacha |

---

## 6. 隱私邊界確認

| 層 | 資料 | 儲存位置 | 違規 |
|----|------|---------|------|
| L1 | `chat_transcripts.content`, `audio_path` | 本地 SQLite | 0 |
| L2 | `role_implicit_states.valence/arousal` | 本地 SQLite | 0 |
| L3 | XP, Badges, Roles, Reflections | Supabase PostgreSQL + RLS | 0 |

`audio_path` 欄位僅儲存本地路徑字串，永不上傳（模型層標注 `# L1: local file path only, never cloud`）。

---

## 7. 後續 Phase 2 銜接

| 項目 | 前置條件 | 狀態 |
|------|---------|------|
| M4.2 Persona State Machine | Phase 1.5 完成 | 🟡 可開始 |
| M2.2 邊緣推論（Gemma E4B） | `role_implicit_states.valence/arousal` 就緒 | 🟡 可開始 |
| M4.13 Task 系統 | `xp_ledger.task_id` 欄位就位 | 🟡 等 Task 模組完成後加 FK |
| `chat_transcripts.paralinguistic_metadata` 解析 | M4.2 完成 | ⏳ M4.2 上線後 |
| Segment.task_id FK constraint | M4.13 完成 | ⏳ M4.13 上線後 |

---

## 8. Git Commits

```
d46e786  fix(M6.2 migration): skip duplicate role_id + move role_implicit_states to local-only
e9b603c  feat(M6.4+M6.5, Phase 1.5): Segment-level reflection & XP settlement
0aef858  docs(phase1_5): Complete preparation summary — all systems ready
1761d11  docs(phase1_5): Refinement assessment + 3-day implementation plan + RISK-13,14
```

Phase 2+ 補強 commit（本次）：
```
[pending]  feat(Phase 2+): RLS all tables + Valence-Arousal local migration + Pydantic models v1.1
```

---

**Phase 1.5 正式關閉。**  
下一行動：Phase 2 — M4.2 Persona State Machine 實作。
