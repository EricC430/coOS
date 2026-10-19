# MVP Closure Report

**日期**：2026-10-19
**依據**：`CLAUDE.md` 鐵則 #4、`docs/06_implementation_phases.md` Phase 5 結尾（「產出 `docs/MVP_CLOSURE_REPORT.md` 後才能進 Phase 6+」）
**盤點基準**：branch `feat/m4-2-episodic-memory-m4-6-topic-anchors` @ `a3084ee`，**含未 commit 的 working tree**（M3.2 / M3.3 / M3.4 前端與 `index.css` 有修改）
**撰寫**：Claude Code（Opus 5.5），由使用者 session 指派；本報告只陳述證據與判定，不修改任何程式碼或其他文件

> 依 `PHASE1_SCOPE_AND_ACCEPTANCE.md` §8 的精神，本報告**不以「N passed」作為主要成果陳述**。主要判定依據是 §4 的閉環逐段證據與 §5 的真實使用數據。本報告**不宣告任何 L2 保真驗收通過**（L2 只能由使用者判定）。

---

## 0. 結論先講

| 項目 | 判定 |
| --- | --- |
| **能否開始 `[進階]` 模組（含 M5 冰山層）** | **NO-GO（條件式）**：差距小，§7 的最小工作量約 1–2 個工作天 + 一次人工走查 |
| 核心閉環是否接通 (L0 接通) | ✅ 程式碼路徑完整，各段都有單元測試；2026-06-21 人工 E2E 通過 7/8 步 |
| 核心閉環是否被真實使用過 (L3) | ❌ 真實資料庫中**草稿核准 0 次**、XP 僅 1 筆（來自 E2E 測試），對話壓縮 (`chat_digest`) **0 筆** |
| 後端測試 | ⚠️ `452 passed / 14 failed / 7 skipped`，14 個失敗全部是 `[進階]` M4.13 的雲端連線錯誤，MVP 模組 0 失敗 |
| 前端測試 | ✅ `40 passed`（7 檔，M3.1–M3.7），GAP-A2 已實質關閉 |
| MVP 模組 29 個 | ✅ 完成 21 ・ ⚠️ 部分完成 7 ・ ❌ 缺 1（M4.7，已決議移出 MVP，但 registry 標籤未同步） |

**NO-GO 的理由不是「東西沒做」，而是三件事還沒被證明：**

1. **測試閘門不是綠的**。過去每份 Closure 的門檻都是 0 failed；目前有 14 個失敗（環境因素，但測試沒有 skip 防護）。
2. **閉環最後一次端到端驗證是 2026-06-21**，之後 2026-08-07 的三個 commit（M4.2 episodic memory、M4.6 topic anchors、M4.2 語氣）改的正是閉環上游；而且那次 E2E 的草稿來源是**遙測斷點**，不是**對話**——「對話 → 草稿」這一段在真實資料裡從未出現過。
3. **`06_implementation_phases.md` 寫明 Phase 6+ 要「MVP 跑通**且收集到至少 100 個使用者真實數據**後再開工」**。目前沒有任何一筆真實核准紀錄。這條是使用者自己訂的門檻，要嘛達成，要嘛由使用者明確拍板豁免（§7 D-1）。

---

## 1. 讀過的文件

`CLAUDE.md`、`docs/06_implementation_phases.md`、`docs/CLOSURE_REPORT_PHASE_0.md` / `_1.md` / `_1.5.md` / `_2.md` / `_3.md` / `_4_5.md` / `_5.5.md`、`docs/IMPLEMENTATION_GAP_REPORT.md`、`docs/SPEC_DEVIATION_REPORT.md`、`docs/PHASE1_SCOPE_AND_ACCEPTANCE.md`、`docs/04_module_registry.md`（MVP 清單）、`docs/MVP_E2E_TEST_REPORT_2026-06-21.md`。

> 注意：`PHASE1_SCOPE_AND_ACCEPTANCE.md` 的「Phase 1」是 2026-08-08 提出的**新階段**（Obsidian Vault 底層接通，草案待拍板），與 `06_implementation_phases.md` 的舊 Phase 1（M0 + M6）不是同一件事。本報告只借用它的四層驗收階梯 (L0–L3) 來描述證據強度。

---

## 2. 測試結果（2026-10-19 本次實跑）

### 2.1 後端 pytest

```bash
cd services && .venv/Scripts/python.exe -m pytest ../testing/ --ignore=../testing/local_llm --ignore=../testing/m0_2 -q
# 14 failed, 452 passed, 7 skipped, 4 warnings in 380.29s
```

| 類別 | 數量 | 內容 |
| --- | --- | --- |
| failed | 14 | **全部**在 `testing/m4_13/test_community_engine.py`（`[進階]` M4.13 社群引擎）。根因相同：`psycopg2.OperationalError ... aws-1-ap-northeast-2.pooler.supabase.com:6543 failed: FATAL: (ENOTFOUND) tenant/user postgres.eajmmzxxfsarmbejpqik not found` |
| skipped | 7 | `m2_2` 邊緣推論離線（`skip_if_edge_offline`）與 `m6_2` / `m6_3` 雲端整合測試（`requires_cloud`：pytest 環境未設 `SUPABASE_DB_URL`） |
| MVP 模組失敗數 | **0** | m0_1 – m6_5 全部通過 |

**判讀**：

- Supabase 回應「tenant/user not found」，代表目前設定的 Supabase 專案**連不上**（可能被暫停或已不存在，本報告無法判定是哪一種，需使用者到 Supabase 後台確認）。這不影響 MVP 本地閉環（XP 與草稿走本地 SQLite，見 §4），但代表 **L3 雲端層目前是斷的**，M6.2 的雲端測試本次也沒有真正跑到。
- `m4_13` 測試沒有像 `m6_2` 一樣掛 `requires_cloud` skip marker，所以雲端一斷就變成失敗而不是跳過——這是測試防護缺口，不是 MVP 邏輯錯誤。
- 與 Phase 5.5 收尾的 `446 passed / 0 failed / 7 skipped` 相比：新增的 6 個 passed 來自 08-07 的 M4.2 / M4.6 新測試，零回歸。

### 2.2 前端與擴充套件 vitest

| 範圍 | 指令 | 結果 |
| --- | --- | --- |
| `apps/desktop`（M3.1–M3.7） | `npx vitest run` | **7 files / 40 passed**（m3_1: 9、m3_2: 6、m3_3: 5、m3_4: 8、m3_5: 5、m3_6: 5、m3_7: 2） |
| `apps/vscode-extension`（M1.3.1） | `npx vitest run` | 1 file / 13 passed |
| `apps/browser-extension`（M1.3.2） | `npx vitest run` | 1 file / 15 passed |

前端測試是真實元件測試（`render(<DraftApproveModal …/>)` 等，import 自 `src/components/`），不是空殼。`IMPLEMENTATION_GAP_REPORT.md` 寫的「`apps/desktop/src` 下 0 個測試」是因為測試放在 `apps/desktop/tests/`，不在 `src/` 底下；這些測試 2026-06-04 就存在了。

### 2.3 本次沒有跑的

- `testing/m0_2`（Tauri IPC，需要 sidecar 在跑）與 `testing/local_llm`（需要 iPad ai.local）——依任務指示排除。
- M1.1 Rust daemon 的 `cargo test`——本次未重跑，沿用 Phase 3 結果。

---

## 3. MVP 模組盤點（29 個，依 `04_module_registry.md`）

狀態定義：✅ 完成 = 程式碼存在、已接線、測試通過；⚠️ 部分 = 主體可用但有已知缺口；❌ 缺 = 不存在。
「測試數」是 `def test_` 函式數（未展開 parametrize），全部在本次 pytest / vitest 中通過，除非另註。

### M0 系統基礎

| 模組 | 狀態 | 程式碼證據 | 測試證據 | 備註 |
| --- | --- | --- | --- | --- |
| M0.1 Monorepo | ✅ | `pnpm-workspace.yaml`、`Cargo.toml`、`services/pyproject.toml` | `testing/m0_1`（6） | |
| M0.2 Tauri IPC / Sidecar | ⚠️ | `apps/desktop/src-tauri/src/{sidecar.rs,commands.rs,socket_server.rs}` | `testing/m0_2`（6，本次排除） | 本次未驗證；`main.py` 的 `/api/tauri/command` 仍是 mock bridge（GAP 報告 D 表） |
| M0.3 .env + Alembic | ✅ | `services/config.py`、`services/alembic/versions`（10）、`services/alembic_cloud/versions`（8） | `testing/m0_3`（8） | |
| M0.4 結構化日誌 | ✅ | `services/m0_4_logging/{schema,writer}.py` | `testing/m0_4`（15） | |

### M1 感知

| 模組 | 狀態 | 程式碼證據 | 測試證據 | 備註 |
| --- | --- | --- | --- | --- |
| M1.1 OS 遙測 (Rust) | ⚠️ | `services/m1_1_telemetry_daemon/` | `testing/m1_1`（16） | Phase 3 記錄的 WPM / 滑鼠 Raw Input = 0 技術債本次未複查；Rust 測試未重跑 |
| M1.2 斷點偵測 | ✅ | `services/m1_2_breakpoint/`（`breakpoint_engine.py` 等 5 檔） | `testing/m1_2`（22） | |
| M1.3 IDE / Browser 擴充 | ⚠️ | `apps/vscode-extension/`、`apps/browser-extension/` | vitest 13 + 15；`testing/m1_3_1`（8）、`m1_3_2`（8） | `.vsix` 打包與 Native Messaging Host 安裝未自動化（Phase 3 技術債，未複查） |
| M1.4 Git 遙測 | ✅ | `services/m1_4_github/` | `testing/m1_4`（15） | |

### M2 邊緣與安全

| 模組 | 狀態 | 程式碼證據 | 測試證據 | 備註 |
| --- | --- | --- | --- | --- |
| M2.1 事件防抖 | ✅ | `services/m2_1_event_debouncer/` | `testing/m2_1`（6） | |
| M2.2 Gemma 邊緣推論 | ✅ | `services/m2_2_gemma/`（含 `chat_compressor.py`） | `testing/m2_2`（12，部分 edge-offline skip） | 程式完整，但真實 DB 中 `chat_digest` 0 筆（§5） |
| M2.3 Eguard 基礎過濾 | ✅ | `services/m2_3_eguard/`（含 `drift_rules.yaml`） | `testing/m2_3`（10） | |

### M3 前端

| 模組 | 狀態 | 程式碼證據 | 測試證據 | 備註 |
| --- | --- | --- | --- | --- |
| M3.1 全域狀態 | ✅ | `apps/desktop/src/stores/m3_1_global_store.ts`、`m3_1_tauri_bridge.ts` | `tests/m3_1`（9） | |
| M3.2 角色儀表板 | ✅ | `src/components/m3_2_dashboard/`（Heatmap、ContextHeaderAggregator、WidgetGridManager…） | `tests/m3_2`（6） | `index.tsx` 有未 commit 修改 |
| M3.3 日報 + 草稿核准 | ✅ | `src/components/m3_3_daily_report/`（`DraftApproveModal/`、`DailyTimeline/`、`ClockwheelNav/`） | `tests/m3_3`（5，含 RISK-01 兩欄必填與「PATCH 先於 XP」） | `TopicGroupView.tsx` 有未 commit 修改 |
| M3.4 AI 幫手對話 | ⚠️ | `src/components/m3_4_ai_helper/`（ExpertSidebar、ChatMessageList、MatchPersonaButton…） | `tests/m3_4`（8） | Typing indicator 未實作（M4.2 backlog #4）；語音輸入仍是 stub（Whisper sidecar 未建） |
| M3.5 成就展示 (基礎) | ✅ | `src/components/m3_5_achievements/` | `tests/m3_5`（5） | Gacha 按鈕 disabled placeholder，符合 RISK-09 |
| M3.6 Workflow Modal | ✅ | `src/components/m3_6_workflow_modal/` | `tests/m3_6`（5） | |

### M4 邏輯層

| 模組 | 狀態 | 程式碼證據 | 測試證據 | 備註 |
| --- | --- | --- | --- | --- |
| M4.1 路由 | ✅ | `services/m4_1_router/` | `testing/m4_1`（29） | DEVIATION-02/03 已拍板「更新 SPEC」 |
| M4.2 Persona 狀態機 | ⚠️ | `services/m4_2_persona/`（15 檔，含 `persona_memory.py`、`reflection_job.py`） | `testing/m4_2`（88） | Backlog：ClaimLedger 仍是每次呼叫新建的記憶體物件（`graph.py:313`）；`reflection_job.py` 存在但沒有被任何排程呼叫；episodic memory 已持久化（`db05f16`、migration `20260803_1100`） |
| M4.3 角色隔離 | ✅ | `services/m4_3_role_isolation/` | `testing/m4_3`（26） | DEVIATION-07 已修：`middleware.py:17` 註明 history / threads / match_persona 已移出豁免清單 |
| M4.4 套問 + 草稿 | ✅ | `services/m4_4_elicitation/`（`controller.py`、`draft_scheduler.py`、`gibbs_template.py`） | `testing/m4_4`（31） | DEVIATION-01 已依拍板落地（`controller.py:113-114`：`MAX_PER_THREAD = 3`、`COOLDOWN_TURNS = 3`、每 context 1 次、confidence 閘）；GAP-C3、GAP-C8 已修（`main.py` 改用 `conversation_turn_counter`） |
| M4.5 XP 結算 | ⚠️ | `services/m4_5_xp_settlement/`（`engine.py`、`zombie_cleanup.py`） | `testing/m4_5`（14） | 實際 API `/api/m4_5/grant_xp`（`main.py:2725`）直接呼叫 `XPGatekeeper.settle_segment_xp`，只檢查 `user_feeling`；`engine.py:87-89` 的 `user_action_plan` 必填檢查**不在這條路徑上**。目前只靠前端按鈕 disabled 擋住 |
| M4.6 Observer | ✅ | `services/m4_6_observer/`（11 檔，含 08-07 新增的 topic anchors） | `testing/m4_6`（48） | GAP-C2 已修（`observer_deps.py:127` 改走 `/api/generate` + `format: json`）；06-21 E2E 第 3 步 Observer 以 curl 測試為 ❌（腳本欄位錯誤），之後未以桌面程式重驗 |
| M4.7 Obsidian 同步 | ❌ | 無任何 `m4_7_*` 程式碼 | 無 | 2026-06-10 已拍板移至 Phase 6，但 `04_module_registry.md:693` 仍標 `[MVP]`、快速統計仍算 29 個 MVP。另 2026-08-08 的 Phase 1 草案又把它拆成 M4.7a/b/c 當新階段主軸——定位需使用者拍板 |

### M6 資料層

| 模組 | 狀態 | 程式碼證據 | 測試證據 | 備註 |
| --- | --- | --- | --- | --- |
| M6.1 本地 SQLite | ✅ | `services/m6_1_sqlite/` | `testing/m6_1`（13） | |
| M6.2 雲端 PostgreSQL | ⚠️ | `services/m6_2_postgresql/`、`alembic_cloud/` | `testing/m6_2`（12，雲端部分 skip） | Supabase 目前連不上（§2.1），雲端 schema 本次無法實測 |
| M6.3 角色情境表 | ✅ | `services/m6_3_role_context/` | `testing/m6_3`（15，雲端部分 skip） | |
| M6.4 日報實體 | ✅ | `services/m6_4_daily_reflections/`（`approve.py`、`models.py`） | `testing/m6_4`（33） | `approve_daily_reflection_flow()` 有完整驗證，但實際 API `PATCH /api/m6_4/reflections/{id}`（`main.py:2682`）是另一條自行組 SQL 的平行路徑，沒有呼叫它 |
| M6.5 ACID 守門員 | ✅ | `services/m6_5_acid_gatekeeper/gatekeeper.py` | `testing/m6_5`（25） | RISK-01 / 13 / 14 守門已實證；抽卡 reward generator 為合規 stub（M3.11） |

**小計**：✅ 21 ・ ⚠️ 7（M0.2、M1.1、M1.3、M3.4、M4.2、M4.5、M6.2）・ ❌ 1（M4.7，已決議移出）。

---

## 4. 核心閉環驗證：對話 → Observer → 草稿 → 使用者核准 → XP

| # | 環節 | 程式碼路徑 | 自動化測試 | 人工 E2E (06-21) | 真實使用數據 |
| --- | --- | --- | --- | --- | --- |
| 1 | 使用者發話 → DRIFT 檢查 → PII 遮蔽 | `main.py:3159` `m4_1_chat`：`_drift_shield.verify_input` → `_eguard_filter.mask_pii(user_msg)` | m2_3、m4_3 | ✅ | `chat_transcripts` 153 筆（最後一筆 2026-06-21） |
| 2 | 路由 → Persona 回應（雲端 Gemini） | `m4_1_router/graph.py` → `m4_2_persona/graph.py::_call_gemini` | m4_1、m4_2 | ⚠️ curl 欄位錯，桌面程式確認可用 | — |
| 3 | 對話落地 L1 | `main.py:3348/3359` `INSERT INTO chat_transcripts` | m6_1 | ✅ | 153 筆 |
| 4 | Observer 背景萃取（主題 / 目標 / 承諾） | `invoke_persona_node._dispatch_observer_bg` → `m4_6_observer/` → SSE | m4_6（48） | ❌（腳本問題，未重驗） | paper_eval 記錄 20 projects + 8 goals 自動萃取（06 月） |
| 5 | M4.4 套問 | `main.py:3296` 起，`ElicitationController` + confidence 閘 | m4_4 | ✅ | — |
| 6 | 對話壓縮為意圖向量 (L2) | `draft_scheduler.py:226-255` 與 `main.py:3381` 呼叫 `ChatCompressor` | m2_2 | 未涵蓋 | **`intent_logs.source_type='chat_digest'` = 0 筆** |
| 7 | 02:00 草稿排程 | `main.py:1219` `draft_cron_loop()` → `run_draft_cron` → SSE `DRAFT_READY` | m4_4（`run_draft_cron` 直接呼叫） | ✅（用手動 `trigger_draft_cron`，草稿來源是**斷點遙測**） | 目前 `daily_reflection_segments` = 0 筆 |
| 8 | 使用者填寫主觀欄位並核准 | 前端 `DraftApproveModal`（兩欄皆填才可按）→ `PATCH /api/m6_4/reflections/{id}` | `tests/m3_3`（RISK-01） | ✅ | **核准 0 次** |
| 9 | XP 結算 | `useApprovalGuard.ts` → `PATCH /api/m4_5/grant_xp` → `XPGatekeeper.settle_segment_xp` | m6_5、m4_5 | ✅（但 E2E 用的是 `/api/m6_5/grant_badge`，不是前端實際呼叫的 `/api/m4_5/grant_xp`） | `xp_ledger` 1 筆（20 XP，2026-06-21，即 E2E 那筆） |

**判定**：

- **L0 接通：✅**。九段程式碼都存在、都有接線、各段有單元測試；`CLAUDE.md` 禁止事項 #1（自動寫 `is_reviewed`）與 #6（未核准發 XP）在程式碼中沒有違反（grep `is_reviewed = 1/True` 只出現在使用者核准路徑 `approve.py:155` 與查詢條件）。
- **但沒有任何一個自動化測試串起整條鏈**（chat → compress → draft → PATCH → grant_xp）。每段各自綠，不代表合起來會動——06-21 E2E 抓出的 BUG-01、06–12 全是「段與段之間」的錯，就是證據。
- **L1 契約：⚠️**。`user_action_plan` 必填只在前端擋；後端 API 可以只帶 `user_feeling` 就核准並拿到 XP（違反 R08 微摩擦力「兩欄必填」的後端防線，見 M4.5 / M6.4 備註）。
- **L3 體感：❌ 沒有數據**。見 §5。

---

## 5. 真實使用數據（本地 `data/coos.db`，唯讀查詢）

| 指標 | 數值 |
| --- | --- |
| `raw_tracking_logs` | 15,387 筆，最後一筆 2026-09-30（遙測持續在收） |
| `chat_transcripts` | 153 筆，最後一筆 2026-06-21 |
| `intent_logs` 中 `chat_digest` | **0** |
| `daily_reflections` / `daily_reflection_segments` | **0 / 0** |
| `xp_ledger` | 1 筆（20 XP，2026-06-21 E2E） |
| `users.current_xp / lifetime_xp` | 20 / 20 |

**需要使用者知道的事**：記憶中的論文數據（`paper_eval_data`）記錄 2026-06 有 198 筆草稿段落、0 筆被核准。這些草稿**現在已不在資料庫裡**。最可能的原因是 `zombie_cleanup.py:90` 的設計行為：未核准、未結算、超過 7 天的草稿會在 app 每小時維護時刪除（RISK-13）。刪除時間本報告無法確定。這代表：

1. 草稿機制產出過大量草稿，但**一張都沒被核准**——閉環的「人」那一端從未發生。
2. 「對話 → 草稿」這段（`chat_digest`）在真實資料中**從未產出過**，06-21 的草稿來自遙測斷點。

另外，`data/coos.db` 與 `data/coos_local.db` 的修改時間落在本次 pytest 執行期間（02:11）。`services/config.py:80` 預設 `local_db_path` 指向 `data/coos.db`，`testing/conftest.py` 沒有覆寫，所以**測試可能會寫入使用者的真實 L1 資料庫**。本次沒有找到任何測試呼叫 `run_zombie_cleanup_sql`，也沒有看到今天的 `raw_tracking_logs` 新紀錄，但測試隔離沒有保證，需要另外確認。

---

## 6. 未解缺口總表

### 6.1 已關閉（本次以程式碼證據確認）

| 編號 | 證據 |
| --- | --- |
| GAP-A2 前端 vitest | `apps/desktop/tests/` 7 檔 40 測試全過（覆蓋率仍偏低，每模組 2–9 個元件測試，無跨元件整合測試） |
| GAP-C2 Gemma `generate_json` | `m4_1_router/observer_deps.py:127-140` 改走 `/api/generate`、`format: "json"` |
| GAP-C3 套問 confidence 閘 | `controller.py:110`、`main.py:3301` import `CONFIDENCE_THRESHOLD` |
| GAP-C8 turn counter 語意 | `main.py` 改用 `app.state.conversation_turn_counter`，每次對話都計 turn |
| DEVIATION-01 套問頻率 | `controller.py:108-114` 依拍板：每 context 1 次、總量 3、cooldown 3 |
| DEVIATION-07 豁免路徑 | `m4_3_role_isolation/middleware.py:17` |
| DEVIATION-09 (b) 送雲前遮蔽 | `main.py:3176-3177` 在進 graph 前 `mask_pii(user_msg)`，且落地的是遮蔽後文字，所以之後撈出的 history 也是遮蔽版 |

### 6.2 仍開放

| 編號 | 內容 | 是否阻擋 `[進階]` |
| --- | --- | --- |
| **TEST-01** | M4.13 測試缺 `requires_cloud` skip marker → 14 failed | **是**（測試閘門） |
| **ENV-01** | Supabase 專案連不上（tenant not found） | 否（MVP 本地閉環不依賴）；但 L3 雲端層與 M3.7 社群目前不可用 |
| **LOOP-01** | 沒有串起整條閉環的自動化整合測試 | **是** |
| **LOOP-02** | 08-07 上游變更後未重做人工 E2E；「對話 → chat_digest → 草稿」從未被真實資料證明 | **是** |
| **LOOP-03** | 後端核准 / 結算路徑未強制 `user_action_plan`；`approve_daily_reflection_flow()` 未被 API 使用 | **是**（R08 微摩擦力的後端防線；改動小） |
| **DATA-01** | 「≥ 100 筆使用者真實數據」門檻（`06_implementation_phases.md:169`）未達：核准 0 次 | **由使用者拍板**（§7 D-1） |
| **TEST-02** | 測試預設寫入真實 `data/coos.db` | 否，但建議在 M5 動工前修（M5 會在本地累積 L1 假設資料，被測試汙染的代價更高） |
| DOC-01 | `04_module_registry.md` M4.7 仍標 `[MVP]`，MVP 總數 29 未更新 | 否（文件同步，決議早已存在） |
| DEVIATION-09 (a) | `02_architecture.md` 尚未寫入「使用者主動發送之對話 = 知情同意通道」條款（`grep 知情同意 docs/02_architecture.md` 無結果） | 否，但 M5 SPEC 依賴此條款界定「什麼可以上雲」，建議一併處理 |
| DEVIATION-13 | `02_architecture.md` 與 `CLAUDE.md` 仍寫冰山圖譜在雲端 Neo4j；`CLAUDE.md` 修改需使用者同意 | 否，但**M5 動工前必須同步**，否則 Claude Code 讀憲章會被導向錯誤架構 |
| M4.2 backlog #1 | ClaimLedger 未持久化 | 否 |
| M4.2 backlog #3 | `reflection_job.py` 未排程 | 否 |
| M4.2 backlog #4 | 前端 typing indicator 未實作 | 否 |
| GAP 報告 D 表 | Tauri IPC bridge mock、語音 stub、`_get_mock_fallback` 未寫 `raw_tracking_logs` | 否 |
| M0.2 / M1.1 | Tauri IPC 測試與 Rust 測試本次未跑 | 否（建議在 LOOP-02 人工走查時一併確認） |

> `CLOSURE_REPORT_PHASE_4_5.md` §7 把 M4.2 backlog 五項全列為進 Phase 6 的前置條件。本報告判斷它們是**品質優化，不影響閉環**，因此不列為阻擋項；若使用者希望維持原本的嚴格標準，§7 需加上 #1、#3、#4。

---

## 7. GO / NO-GO 判定與最小工作量

### 判定：**NO-GO（條件式）**

MVP 的程式碼已經到位，差的是**證明**。下列工作完成後即可改判 GO，不需要新增任何 MVP 功能。

### 7.1 最小必要工作（完成即 GO）

| # | 工作 | 預估 | 完成定義 |
| --- | --- | --- | --- |
| W1 | `testing/m4_13/test_community_engine.py` 加上與 `m6_2` 相同的 `requires_cloud` skip marker（或修復 Supabase 連線） | 0.5 小時 | pytest `0 failed` |
| W2 | 後端核准 / 結算路徑補 `user_action_plan` 非空檢查（`PATCH /api/m6_4/reflections` 在 `is_reviewed=true` 時、或 `grant_xp` 改走 `engine.py` 的三重守門），並補一個「只填 feeling 不可拿 XP」的測試 | 1–2 小時 | 新測試綠；`[R08: 微摩擦力 §四.2]` 有後端防線 |
| W3 | 新增一個閉環整合測試：暫存 SQLite → 寫入 chat_transcripts → `ChatCompressor` 產出 `chat_digest` → `run_draft_cron` → PATCH 核准 → `grant_xp` → 斷言 `xp_ledger` +1、再呼叫一次不重複發放 | 半天 | 測試綠，且使用暫存 DB 不碰 `data/coos.db` |
| W4 | 照 Phase 5 八步驟用**桌面程式**重做一次人工 E2E，重點補驗：(a) 第 3 步 Observer 偵測；(b) 草稿來源是**對話**而非斷點；(c) 第 7 步走前端真正呼叫的 `/api/m4_5/grant_xp`；(d) M0.2 Tauri IPC | 1–2 小時（人工） | 新的 `docs/MVP_E2E_TEST_REPORT_<日期>.md`，每步附截圖或 DB 查詢 |
| W5 | `04_module_registry.md` 將 M4.7 標籤改為已移出 MVP（依 06-10 決議）並更新快速統計 | 10 分鐘 | registry 與 `06_implementation_phases.md` 一致 |

### 7.2 需要使用者拍板的事

| # | 問題 | 為何擋著 |
| --- | --- | --- |
| **D-1** | 「≥ 100 筆使用者真實數據才開 Phase 6+」要不要維持？若維持，「數據」指什麼（100 次核准？100 天？100 段草稿？）若豁免，請明確寫入 `06_implementation_phases.md` | 這是使用者自訂的門檻；目前核准 0 次。M5 冰山層的證據萃取 (M5.2) 完全依賴真實對話與反應，沒有真實數據就無從驗證 M5 有沒有效 |
| D-2 | 被 zombie cleanup 刪掉的 198 筆未核准草稿：是否要調整 7 天門檻，或先確認這是預期行為？ | 屬 RISK-13 研究約束的參數，修改需使用者同意 |
| D-3 | M4.7 的定位：維持「Phase 6 進階」，還是依 `PHASE1_SCOPE_AND_ACCEPTANCE.md` 升為下一階段主軸 (M4.7a/b/c)？ | 跨模組職責邊界調整，需使用者決定；也決定 M5 與 Vault 工作的先後 |

### 7.2b 拍板結果（2026-10-19，使用者）

| # | 決議 | 對後續的影響 |
| --- | --- | --- |
| **D-1** | **不維持**「≥ 100 筆真實數據」門檻，改以**合成使用者模擬**產生數據。 | Phase 6+ 的資料門檻改為「合成使用者模擬器 (§7.4) 可跑完一輪模擬」。已在技能 / 外掛目錄搜尋過：TDCv2、SpiceGrinder 等只產生表格式假資料（姓名、地址、資料表種子），**無法**模擬「同一個人連續數週的對話、遙測、反思，以及對介入的心理反應」，因此需在專案內自建模擬器。 |
| **D-2** | 198 筆被 zombie cleanup 刪除的草稿是**預期行為**；7 天門檻維持不變 (RISK-13 不改)。使用者說明：當時沒有時間核准，且草稿品質未達標準 —— **分散過多、辨識不清**，無法負荷逐一核准。 | 真正的問題是**草稿品質造成核准疲勞**，不是清理機制。佐證：§5 指出真實資料中的草稿全部來自遙測斷點、沒有一張來自對話，遙測切塊天然會產生大量零碎卡片。這是 `DESIGN_PHILOSOPHY_AUDIT.md` 判斷一所說的「記錄疲勞死亡曲線」在 coOS 本身重演，見 §7.3 第一項 (W6)。 |
| **D-3** | 交由 Claude 決定 → **M4.7a Vault Governance Reader (唯讀) 升為下一階段主軸，排在 M5 之前**；M4.7b Writer、M4.7c 事件匯流排維持 `PHASE1_SCOPE_AND_ACCEPTANCE.md` 原定順序，但**不擋** M5。 | 理由見 §7.5。 |

### 7.3 建議在 M5 動工前一併處理（非 GO 條件）

- **W6（最高優先，D-2 衍生）草稿收斂**：讓每日草稿從「每個遙測區塊一張」收斂為「每個專案 / 主題一張」，並以 M4.7a 匯入的 Projects 與 M4.6 主題錨點作為分組依據；卡片標題必須能讓使用者一眼認出是哪件事。完成定義：以同一天的真實遙測重跑，草稿數下降且每張可對應到一個已知專案或主題。M5.2 只讀**已核准**的反思作為證據，草稿若繼續無人核准，冰山層將缺少最重要的自陳證據。

- **DEVIATION-13**：同步 `02_architecture.md` 與 `CLAUDE.md` 的 Neo4j 描述（`CLAUDE.md` 需使用者同意）。
- **DEVIATION-09 (a)**：在 `02_architecture.md` 寫入知情同意通道條款，M5.6 洩漏閘需要這條來界定邊界。
- **TEST-02**：讓測試預設使用暫存 DB（例如 conftest 覆寫 `local_db_path`）。M5 會在本地累積 L1 冰山假設，測試汙染真實資料庫的代價會更高。

---

### 7.4 合成使用者模擬器（D-1 衍生，建議模組編號 M0.5，屬測試基礎設施）

- **作法**：每位合成使用者帶一份**事先寫好的真實答案冰山** (行為 → 應對姿態 → 感受 → 觀點 → 期待 → 渴望) 與 OCEAN 人格條件 [R13: PersonaLLM §Personality Conditioning]，以 Generative Agents 式的記憶流與定期反思維持跨日一致 [R11: Generative Agents §3.1 Memory Stream] [R11: Generative Agents §3.3 Reflection]。模擬器逐日產生對話、遙測事件、Git 事件、反思草稿的核准與填寫，並依照自己的冰山與準備度回應 coOS 的介入 (會共鳴、會防衛、會婉拒實驗)。
- **最大價值**：真實資料無法得知「正確答案」，合成使用者可以。因此可量測 M5.2 / M5.3 推論出的冰山與預設答案的**精確率 / 召回率**、反應分類器是否把防衛誤判為證實 (RISK-21)、守門規則是否在低落期擋下碰撞 (RISK-20)。
- **隔離**：寫入獨立的 `data/coos_synthetic.db`，每列帶 `is_synthetic = 1`；絕不寫入 `data/coos.db`，也不得混入論文的 N=1 真實數據 (`paper_eval_data`)。合成使用者沒有真實個資，可使用雲端 LLM 扮演。
- **限制 (論文中須明說)**：合成數據證明的是**機制正確與推論準確度**，**不能**證明真人會因此產生改變。

### 7.5 D-3 決策理由：為什麼 M4.7a 排在 M5 之前

1. **冷啟動是空的**：目前 role、goals、heatmap 都是空的。M4.7a 一次匯入 10 個 Role、130 個 Skill、45 個 active Project、6 條 Principle，儀表板、路由、PersonaCard 立刻有真實內容 (`DESIGN_PHILOSOPHY_AUDIT.md` §3.5 評為單位工時價值最高)。
2. **直接解 D-2**：草稿「分散、辨識不清」的一大原因是系統不知道使用者有哪些專案，只能依遙測時間切塊。有了 Vault 的 Projects，W6 的草稿收斂才有分組依據。
3. **M5 需要它**：Vault 的 Principles 可成為 PersonaCard 立場與 M5.5 小實驗的素材；已核准的反思是 M5.2 最重要的證據來源，必須先讓核准率回升。
4. **風險低**：M4.7a 是唯讀加週期重掃，不寫 Vault，不碰隱私邊界的寫入面。M4.7b / M4.7c 涉及寫回與 `CLAUDE.md` 新鐵則，維持原排程，且不擋 M5。

**建議順序**：W1–W5 (排程中) → W4 人工 E2E → M4.7a + W6 草稿收斂 → M0.5 合成使用者模擬器 → M5 P1 (假設庫 + 冰山之鏡唯讀)。注意：M4.7a 的「文件入憲」部分需要修改 `CLAUDE.md`，屆時須先取得使用者同意。

## 8. 本報告的驗證方式

```bash
# 後端
cd services && .venv/Scripts/python.exe -m pytest ../testing/ --ignore=../testing/local_llm --ignore=../testing/m0_2 -q
# → 14 failed, 452 passed, 7 skipped, 4 warnings in 380.29s

# 前端 / 擴充套件
cd apps/desktop && npx vitest run            # → 7 files, 40 passed
cd apps/vscode-extension && npx vitest run   # → 13 passed
cd apps/browser-extension && npx vitest run  # → 15 passed

# 真實使用數據：以 sqlite3 唯讀模式 (file:...?mode=ro) 查詢 data/coos.db
```

**未驗證**：M0.2 Tauri IPC、M1.1 Rust 測試、ai.local 邊緣推論、Supabase 雲端層、實際 02:00 cron 觸發（只驗證過手動觸發）、任何 L2 保真與 L3 體感。

---

## 9. 修補紀錄 (2026-10-19 排程執行)

> 本節由排程任務 `coos-mvp-closure-w1-w5` 自動執行並撰寫，使用者未在場。所有變更**未提交** (無 commit / push / stash / 切換分支)，請審閱 `git diff` 後再決定。

### 9.1 各項狀態

| # | 狀態 | 改了哪些檔案 | 新增 / 調整的測試 |
| --- | --- | --- | --- |
| W1 | ✅ 完成 | `testing/m4_13/test_community_engine.py`：比照 `testing/m6_2` 加模組層級 `requires_cloud` (`SUPABASE_DB_URL` 未設定即 skip) | 14 個 M4.13 測試由 failed 轉為 skipped |
| W2 | ✅ 完成 (超出原估：順手修了 2 個阻斷性 bug，見 9.2) | `services/m6_5_acid_gatekeeper/gatekeeper.py`：`settle_segment_xp` 與 `settle_earned_xp` 核心守門加 `user_action_plan` 非空檢查 (`GATEKEEPER_001` / `missing_user_action_plan`)；`services/main.py`：`/api/m4_5/grant_xp` 改用快照 store 呼叫守門員、`/api/m6_5/grant_badge` 補同一檢查 | `testing/m6_5/test_segment_settlement.py::test_feeling_only_segment_gets_no_xp` (×3：None / 空字串 / 空白)、`testing/m6_5/test_acid_gatekeeper.py::test_xp_blocked_feeling_only`；既有 3 個「已核准」fixture 補上 `user_action_plan` (它們原本代表「只填 feeling 就核准」，正是本次要擋的情況) |
| W3 | ✅ 完成 | `testing/m4_5/test_mvp_closed_loop.py` (新)；`services/m4_4_elicitation/draft_scheduler.py` (修 import bug，見 9.2) | `test_chat_to_xp_closed_loop`、`test_feeling_only_approval_earns_no_xp` |
| W4 | ⏳ 待使用者人工 E2E | — | — |
| W5 | ✅ 完成 | `docs/04_module_registry.md`：M4.7 標籤 `[MVP]` → `[進階]` 並加 2026-06-10 移出 / 2026-10-19 D-3 註記；快速統計 MVP 29 → 28 | — |
| D-1 ~ D-3 | ■ 已拍板 (見 §7.2b) | — | — |

**W2 的選擇理由**：把 `user_action_plan` 檢查放進 M6.5 `XPGatekeeper` 的核心守門，而不是放在 `PATCH /api/m6_4/reflections`。守門員是所有 Earned XP 的唯一入口 (CLAUDE.md 禁止事項 #6)，放這裡一處就同時保護 `grant_xp` 與日後任何呼叫端；PATCH 是部分更新，若在 PATCH 擋，需先讀回舊列才能判斷，改動較大。`grant_badge` 是另一條自寫 SQL 的 XP 路徑，所以另外補一行同樣的檢查。註解使用 `[R08: 微摩擦力 §四.2]` 與 RISK-01 格式。`is_reviewed=true` 仍只由使用者的 PATCH 寫入，沒有任何程式自動寫入。

**整合風險稽核 (CLAUDE.md §5，M6.4 + M4.5 + M6.5)**：觸發 RISK-01 (緩解 = 本次三重守門補齊後端防線，測試已補)、RISK-13 (`is_active` 守門未動，`SegmentObj` 在 MVP 恆為 active)、RISK-14 (閉環測試斷言 `current_xp == lifetime_xp == amount`)。排程模式下使用者不在場，稽核結論未經使用者確認即動工 (任務檔已明確指派 W2)。

### 9.2 本次發現並修正的問題 (W3 閉環測試抓到的「段與段之間」錯誤)

這三個 bug 都是單元測試各自綠、合起來就壞的典型例子，也解釋了 §4 / §5 的兩個謎：

1. **`PATCH /api/m4_5/grant_xp` 每次呼叫都 500** (前端 `useApprovalGuard.ts` 實際呼叫的端點)。`XPGatekeeper` 是同步程式，但 `LiveXPStore` 的 proxy 是 async，`segments.get()` 回傳未 await 的 coroutine → `AttributeError: 'coroutine' object has no attribute 'is_active'`。06-21 E2E 用的是 `/api/m6_5/grant_badge`，所以沒抓到。**這代表透過桌面程式核准草稿從來拿不到 XP。** 修法：在端點內先 await 取回 segment / user，放進 `SimpleNamespace` 快照交給守門員，成功後再 await 寫回 segment、user 與 ledger。
2. **XP 與結算旗標寫入時無聲失敗**。`UserObj.save` 寫了本地 `users` 表沒有的 `updated_at` 欄；`SegmentObj.save` 寫了 `daily_reflection_segments` 沒有的 `xp_settled_at` / `earned_xp` 欄。`AsyncDBAdapter.execute` 會吞掉錯誤只記 warning，結果 `current_xp` 不會增加、`xp_settled` 不會變 1 (可以重複領)。修法：只寫存在的欄位。
3. **02:00 排程的對話壓縮從未執行**。`draft_scheduler._compress_undigested_threads` 用 `from config import settings`，但 `config.py` 只提供 `get_settings()`，每次都 ImportError 後靜默 return。**這就是 §5 `chat_digest = 0` 的原因。** 修法：改用 `_get_gemma_model()`；同檔的 `_get_ai_local_host()` / `_get_gemma_model()` 也有同樣錯誤 (過去一直退回寫死的 `192.168.0.79` 預設值)，一併改為 `get_settings()`。

### 9.3 發現但**未修**的問題 (需使用者決定或屬後續工作)

| 編號 | 內容 | 為什麼沒修 |
| --- | --- | --- |
| LOOP-05 | `draft_scheduler._get_gemini_key()` 也是 `from config import settings`，所以排程草稿從未用 `.env` 的 Gemini key (除非系統環境變數另有設定)，一直走本地 Gemma / 範本 | 修好會**開啟一條過去實際上沒在運作的雲端呼叫路徑**，屬隱私邊界行為變更，需使用者決定 |
| LOOP-06 | `main.py` 主題分組 (`topic_groups`，約第 2592 行) 也是 `from config import settings as _cfg`，Gemma 分組永遠失敗退回關鍵字分組 | 與 W6 草稿收斂直接相關，建議在 W6 一併處理 |
| LOOP-07 | `/api/m6_5/draw_card` 與 `grant_xp` 有同樣的同步守門員 + async proxy 問題，呼叫必定失敗 | 屬 `[進階]` M3.11 Gacha，不在 MVP 閉環內 |
| LOOP-08 | 草稿**只**從遙測 (`focus_session_ended`) 產生；當天只有對話、沒有遙測時 `generate_draft` 回傳 None。`chat_digest` 只是補充草稿脈絡，不會自己產生卡片 | 這是設計問題 (「草稿來源是對話」是否成立)，W4 第 (b) 點與 W6 需要先釐清預期 |
| LOOP-09 | 時區混用：時間戳以 UTC 寫入，但 `date(created_at) = :for_date` 用本地日期比對。UTC+8 下 02:00 排程剛好落在前一天 UTC，所以目前能動；本地 00:00–08:00 的對話會被歸到前一天 | 非確定性錯誤，需決定統一用本地日或 UTC |
| `grant_xp` reflection 分支 | 只在找不到 segment 時才走，`daily_reflections` 沒有 `is_draft` / `xp_settled` 欄，該分支同樣不能用 | MVP 一律以 segment 結算，這條是舊 API 殘留；未動 |
| TEST-02 | 全套 pytest 執行後 `data/coos.db`、`data/coos_local.db` 的修改時間再次變動 (07:14，大小不變)。新的閉環測試本身有斷言不碰真實 DB 並通過，但其他既有測試仍會開啟真實檔 | 任務範圍外 (§7.3)，建議 M5 前以 conftest 全域覆寫 `local_db_path` |

### 9.4 最終測試結果

```bash
cd services && .venv/Scripts/python.exe -m pytest ../testing/ --ignore=../testing/local_llm --ignore=../testing/m0_2 -q
# 458 passed, 21 skipped, 5 warnings in 317.98s   (0 failed)
```

- passed 452 → 458：新增 6 個 (W2 ×4、W3 ×2)。
- skipped 7 → 21：多出的 14 個是 W1 的 M4.13 雲端測試。
- `uv run ruff check --fix` 已對改過的測試檔、`gatekeeper.py`、`draft_scheduler.py` 執行 (僅自動整理 import 順序與移除 2 個未使用 import)。`main.py` 原本就有 52 個 lint 錯誤，未加 `--fix` 以免動到無關程式碼；改動前後數量相同，本次沒有新增。
- 未重跑：前端 vitest (本次未改前端)、M0.2 Tauri IPC、M1.1 Rust。

### 9.5 GO / NO-GO 判定更新

**判定：待人工 E2E，完成即 GO。**

W1、W2、W3、W5 已完成，pytest 0 failed，閉環已有自動化測試證明 (LOOP-01、LOOP-03、TEST-01、DOC-01 關閉)。剩下 W4 需使用者親自用桌面程式走一次；因為 9.2 修掉的 bug 正好在 W4 要驗的 (b)(c) 兩點上，請特別確認：

1. 前端核准後 `xp_ledger` 新增一筆、`users.current_xp` 增加，且再按一次不會重複 (9.2 #1、#2)。
2. 隔天 02:00 (或手動 `trigger_draft_cron`) 後 `intent_logs` 出現 `source_type='chat_digest'` (9.2 #3)。
3. LOOP-08：當天只聊天、沒有遙測時預期會不會有草稿。
