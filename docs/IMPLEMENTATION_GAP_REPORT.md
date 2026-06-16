# 實作缺口報告 (Implementation Gap Report)

**日期**：2026-06-10（最後更新：2026-06-13 Session 3 缺口全數補齊）
**範圍**：截至 Phase 4/5 收尾，所有「**生成時偏離 SPEC、沒接上、未完成、被省略、或仍是模擬/stub**」的部分
**與 SPEC_DEVIATION_REPORT.md 的分工**：那份處理「行為改了、需要拍板」；本份處理「東西不存在、沒接線、或是假的」。

> 分類：
> - **A 未實作** — 模組/功能完全不存在
> - **B 沒接上** — 程式碼存在但從未被呼叫/掛載（dead code）
> - **C 半成品** — 接上了但缺關鍵子環節
> - **D 模擬/Stub** — 刻意的假實作（含合規 stub 與待換真品）

---

## A. 未實作

### GAP-A1 ❌ M4.7 Obsidian 同步（Phase 4 範圍內）
`services/` 無任何 `m4_7_*`。`docs/modules/M4_7_obsidian_sync_SPEC.md` 存在但零程式碼。
**處置選項**：補實作，或在 `04_module_registry.md` / `06_implementation_phases.md` 將其移出 Phase 4（需使用者拍板，屬職責邊界調整）。

### GAP-A2 ❌ 前端 vitest 驗收測試（M3.1–M3.6 全部）
`apps/desktop/src` 下 **0 個** `*.test.*` 檔案。各 M3 SPEC 的 Acceptance Criteria 皆以 vitest 撰寫（如 M3.4「未配對 Persona 不可點」「語音按鈕走 VoiceTranscriptionRouter」），違反 CLAUDE.md 鐵則 3「先寫測試」。

### GAP-A3 ✅ `drift_rules.yaml` 缺檔（已修 Session 2）
`services/m2_3_eguard/drift_rules.yaml` 已建立，77 條關鍵字（英/中）。

### GAP-A4 ✅ RISK-17 最後一個專家刪除守門員（已修 Session 3）

- 後端：`DELETE /api/m4_1/experts/{id}?role_id=` 軟刪除 + `EXPERT_POOL_EMPTY` SSE 廣播
- 前端 `ExpertItem`：hover 顯示 ✕ 刪除按鈕
- 前端 `ExpertSidebar`：最後一位時彈出確認框（`data-testid="last-expert-confirm-modal"`）
- `MultiAgentHelper`：`handleDeleteExpert` 呼叫後端、清 expertCache、切回工具型 AI

---

## B. 沒接上（dead code）

### GAP-B1 ✅ M4.4.3 深夜草稿排程器（已修 Session 2）

`run_draft_cron` 已掛載 lifespan 02:00 cron；`AsyncDBAdapter` 已實作所有 4 個 DB 方法。

### GAP-B2 ✅ M4.2 message_splitter 未入圖（已修 Session 2）

`build_persona_graph()` 已插入 `message_splitter` 節點，`PersonaState.split_messages` 回傳多氣泡序列。

### GAP-B3 ✅ M4.2 [記憶區塊] 永遠為空（已修 Session 2）

`persona_responder_node` 現傳入 `persona_id / active_goals / upcoming_promises`；M4.1 `router_input` 與 `persona_input` 同步補上。

### GAP-B4 ✅ M4.5 殭屍清理模組被繞過（已修 Session 3）

`m4_5_xp_settlement/zombie_cleanup.py` 新增 `run_zombie_cleanup_sql()`；`main.py` lifespan 改呼叫此函式，內聯 DELETE 已移除。`[RISK-13]` WHERE 條件正確（`is_draft=1 AND is_reviewed=0`）。

### GAP-B5 ✅ M4.6 Observer 雙軌並行（已修 Session 3）

`main.py` chat 端點的內聯 `detect_and_upsert_project` 已移除；統一走 `invoke_persona_node._dispatch_observer_bg`。`observer_deps._resolve_sse()` 已改接真實 `_sse_broadcast`（GAP-C1 同步修復）。

---

## C. 半成品

### GAP-C1 ✅ M4.6 Observer SSE 介面是 mock（已修 Session 3）

`observer_deps.py::_resolve_sse` 改為連接真實 `main._sse_broadcast`，透過 `_SSEAdapter` 包裝。Observer 萃取的 GOAL_INFERRED / PROMISE_DETECTED 事件現能廣播至前端 SSE 訂閱者。

### GAP-C2 ⚠️ Gemma adapter 的 generate_json 語意錯位（待修，Phase 6）

`observer_deps.py::_GemmaAdapter.generate_json` 呼叫 `pipeline._client.generate()`（回傳意圖向量 dict），`promise_extractor` workaround「dict 進來就回 []」仍存在。Gemma 路徑承諾萃取空轉。需配合本地 LLM API 設計 JSON 結構化輸出通道。

### GAP-C3 ⚠️ M4.4 套問缺 telemetry confidence 檢查（待修，Phase 5 收尾）

SPEC §5「自信度 ≥ 0.7 不觸發套問」——main.py 注入路徑未讀 `TelemetrySegmentReport`。

### GAP-C4 ✅ 配對問候語不落地（已修 Session 2）

`/api/m4_1/confirm_match` 端點：M4.2 persona graph 生成問候 → 落地 `chat_transcripts`；前端預覽卡確認後呼叫此端點。

### GAP-C5 ✅ `_ai_generate_expert` 生成品質無校驗（已修 Session 3）

JSON 解析後新增：(1) `_FORBIDDEN_PHRASES` 禁用語檢查（含「我是AI」等通用語句）；(2) `_CONCRETENESS_MARKERS` 具體性檢查（需含年代/學經歷標記）。任一不通過 → `return None`，不入庫。

### GAP-C6 ✅ m2_3 `verify_input` async 呼叫端（已修 Session 2）

`main.py` 三處 DRIFT Shield 呼叫均補 `await`；5 個測試改為 `async def`。

### GAP-C7 ✅ chat_history 撈取方向錯誤（已修 Session 2）

改為 `ORDER BY created_at DESC LIMIT 12` 後 `reversed()`，確保取最近 12 條。

### GAP-C8 ⚠️ Elicitation turn counter 語意不同步（待修，Phase 5 收尾）

`app.state.elicitation_turn_counter` 是注入嘗試次數非對話 turn 數。DEVIATION-01 拍板後需修正單位，使 cooldown 以實際對話輪次計算。

---

## D. 模擬 / Stub（標注哪些是合規、哪些待換真品）

| 項目 | 位置 | 性質 |
|------|------|------|
| Google OAuth 全套 | `main.py` `/api/auth/google/*`（`stub: true`）、Onboarding `oauthStub` UI | ✅ 合規 stub（L3 多裝置同步為 Phase 6+；CI 已豁免） |
| M3.7 社群 UI | `m3_7_community/index.tsx` `stubMode=true` | ✅ 合規 stub（Phase 6b；SPEC 明定不可移除） |
| M3.5 Gacha 按鈕 | `m3_5_achievements` disabled placeholder | ✅ 合規（RISK-09，M3.11 解鎖） |
| 語音輸入 | `useVoiceInput.ts`「Stubs -- real implementations connect to local Whisper sidecar」 | ⏳ 待換真品（Whisper sidecar 未建） |
| M1.2.2 Tauri IPC bridge | `main.py:2613`「Mock Tauri IPC command bridge」 | ⏳ 待換真品（通知靜音需 Rust 端） |
| AsyncDBAdapter mock fallback | `main.py::_get_mock_fallback`（PG 失敗回空清單） | ⏳ 可接受的降級，但需在 raw_tracking_logs 記 fallback 事件（目前只有 logger.warning） |
| 工具型 AI 緊急罐頭回覆 | `m4_1_router/graph.py::_TOOL_FALLBACK_RESPONSES`（4 句輪替） | ✅ 合理 fallback（僅 Gemini 全掛時） |
| M6.5 抽卡 reward generator | `m6_5_acid_gatekeeper/gatekeeper.py:305`「Stub reward generator (M3.11 will replace)」 | ✅ 合規（Phase 6b） |
| Observer noop handler | `m4_6_observer/agent.py::_noop_impl` | ✅ 預設佔位，有真實 impl 注入點 |

---

## 修復狀態總覽（2026-06-13）

| 項目 | 狀態 | Session |
|------|------|---------|
| GAP-A1 M4.7 Obsidian | ➡️ 移至 Phase 6 | 拍板 |
| GAP-A2 前端 vitest 測試 | ❌ 未實作 | Phase 6 前補齊 |
| GAP-A3 drift_rules.yaml | ✅ 已修 | Session 2 |
| GAP-A4 最後專家刪除守門員 | ✅ 已修 | Session 3 |
| GAP-B1 草稿排程器 | ✅ 已修 | Session 2 |
| GAP-B2 message_splitter | ✅ 已修 | Session 2 |
| GAP-B3 記憶區塊接線 | ✅ 已修 | Session 2 |
| GAP-B4 zombie_cleanup 被繞過 | ✅ 已修 | Session 3 |
| GAP-B5 Observer 雙軌 | ✅ 已修 | Session 3 |
| GAP-C1 Observer SSE mock | ✅ 已修 | Session 3 |
| GAP-C2 Gemma generate_json | ⚠️ 待修 | Phase 6 |
| GAP-C3 telemetry confidence | ⚠️ 待修 | Phase 5 收尾 |
| GAP-C4 問候語不落地 | ✅ 已修 | Session 2 |
| GAP-C5 expert 品質無校驗 | ✅ 已修 | Session 3 |
| GAP-C6 DRIFT async 迴歸 | ✅ 已修 | Session 2 |
| GAP-C7 歷史方向錯誤 | ✅ 已修 | Session 2 |
| GAP-C8 turn counter 語意 | ⚠️ 待修 | Phase 5 收尾 |

**測試結果（Session 3 結尾）**：`407 passed / 0 failed / 7 skipped`
