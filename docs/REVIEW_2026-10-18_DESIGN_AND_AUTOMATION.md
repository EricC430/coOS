# 設計審查與自動化報告 (2026-10-18)

**分支**：`claude/design-review-2026-10-18`（基底 `feat/m4-2-episodic-memory-m4-6-topic-anchors` @ `a3084ee`）
**範圍**：`docs/` 設計文件 vs. `services/`、`apps/`、`testing/` 實際程式碼

**方法與限制**

- 本次先由雲端排程 agent 執行審查，但它沒有 GitHub 推送權限，結果留在雲端沙箱。本報告是在本機依它的發現重做，**每一項都重新對照本機程式碼確認過**，附檔案與行號。
- SPEC 驗收測試覆蓋率是**依測試函式名稱比對**，實際測試若改了名字會被算成「缺」。數字是上限估計，不是精確值。
- 研究引用一律對照 `docs/03_research_index.md` 既有編號，沒有新增編號。

---

## 1. 需要改進的模組

| # | 模組 | 問題 | 證據 | 建議 | 分類 |
|---|------|------|------|------|------|
| 1 | M4.2 / M4.1 | **對話逐字稿（L1）直送雲端 Gemini，送出前沒有 PII 遮蔽**。違反 CLAUDE.md 隱私三層原則與「不要做的事 #2」。[R07: POST §4.3] 要求上雲前先壓縮為意圖向量、不傳明文 | `services/m4_2_persona/graph.py:234`（`_call_gemini` 帶入 `chat_history`）、`:422-423`（最多 16 條歷史）；該檔無任何 `mask_pii` / `EguardFilter` 呼叫。`EguardFilter.mask_pii` 已存在於 `services/m2_3_eguard/filter.py:56` | 見決策 D1。不論選哪個方案，`mask_pii` 都該先補 | 👤 |
| 2 | M4.4 | **套問的 telemetry confidence 檢查沒有生效**。SPEC §5「confidence ≥ 0.7 不觸發」（「AI 裝傻」反模式，SPEC §8；[R08: 微干預 §五]） | `services/main.py` M4.4 注入區塊呼叫 `ec.can_elicit(resolved_thread_id, conv_turn, context=...)`，沒有傳入 confidence | 決定資料來源後接上（決策 D4） | 👤 |
| 3 | M4.2 | **trust_level 起始值有三種**：SPEC §9 拍板 0.5，但 fallback 用 0.7、API 回傳寫死 0.8。[R05: 副語言線索 §跨越恐怖谷] 的注入率 `0.08 × (1.5 − trust)` 會跟著變（0.5→8%、0.8→5.6%） | `services/m4_1_router/graph.py:223,231`（0.7）、`services/main.py:2109`（`"trustLevel": 0.8`）、`services/m4_2_persona/graph.py:158,263`（0.5） | 拍板後統一（決策 D3，即 DEVIATION-08） | 👤 |
| 4 | M4.13 / M6.6 / M3.7 | **`[進階]` 模組已經硬接進 MVP 主程式**，違反 CLAUDE.md 鐵則 4 與「不要做的事 #7」（MVP 必須能在進階模組全數移除時獨立運作）。`docs/MVP_CLOSURE_REPORT.md` 尚不存在 | `services/main.py:49` 頂層 `from m4_13_community_engine.routes import ...`、`:1402` `app.include_router(...)`；`docs/04_module_registry.md:446,744,895` 標 `[進階]` | 決策 D2 | 👤 |
| 5 | M4.7 | **兩份文件分級互相矛盾**：registry 標 `[MVP]`，phases 說 2026-06-10 已拍板移到 Phase 6 | `docs/04_module_registry.md:653` vs. `docs/06_implementation_phases.md:81` | 拍板已經做過，只差同步 registry 標籤（決策 D5，需確認） | 👤 |
| 6 | M6.1 | `raw_content_stores` 在 SPEC §7.5 有定義、M2.2 SPEC 也會讀它，但**從未建表** | `docs/modules/M6_1_sqlite_schemas_SPEC.md:302-311`；`docs/modules/M2_2_gemma_edge_inference_SPEC.md:30` | 已補 migration 與測試（見 §3） | 🤖 ✅ |
| 7 | M0.2 | sidecar 沒啟動時 5 項測試直接失敗，沒有照 CLAUDE.md 規則 8 加 skip marker | `testing/m0_2/test_tauri_ipc.py` | 已補（見 §3） | 🤖 ✅ |
| 8 | 文件 | `02_architecture.md` 配額表有兩列 `Gemma 4 26B`（DEVIATION-12） | `docs/02_architecture.md:172-173` | 已修（見 §3） | 🤖 ✅ |
| 9 | 文件 | GAP / DEVIATION 追蹤表狀態過時：GAP-A2、GAP-C8、DEVIATION-07 其實已完成 | `apps/desktop/tests/m3_*`；`services/main.py` 的 `conversation_turn_counter`；`services/m4_3_role_isolation/middleware.py:15-34` | 已同步（見 §3） | 🤖 ✅ |
| 10 | M6.3 | 雲端 migration docstring 寫「role_implicit_states: add valence/arousal/raw_triggers」，但同檔程式碼註明此表 LOCAL-ONLY、沒有動到。**程式碼本身符合 SPEC**，只有說明文字誤導 | `services/alembic_cloud/versions/20260531_1100_m6_2_refinement_ledger.py:13` vs. `:83,89` | 改 docstring 一行即可。為了不改既有的 migration 歷史檔，本次沒動 | 🤖 未做 |
| 11 | 多模組 | 多數 SPEC §6 的驗收測試名稱在 `testing/` 找不到對應（見 §2） | 見 §2 表格 | 逐模組補測試 | 🤖 / 👤 混合 |
| 12 | 全域 | ruff 剩 74 項無法自動修（E712 `== True`、E501 行過長、F841 未使用變數等） | `uv run ruff check .` | E712 改 SQLAlchemy `.is_(True)` 需逐一看語意，建議另開一次清理 | 🤖 未做 |

---

## 2. SPEC 驗收測試覆蓋（依名稱比對）

只列有缺的模組。`spec` = SPEC §6 列出的測試數，`缺` = `testing/` 或 `apps/desktop/tests/` 找不到同名測試的數量。

| 模組 | spec | 缺 | 備註 |
|------|------|----|------|
| M0.2 Tauri IPC | 6 | 2 | 缺的 2 項是 Rust `invoke`，需要 Tauri 執行環境 |
| M0.3 env/alembic | 8 | 1 | |
| M0.4 structured logging | 6 | 1 | |
| M1.1 OS telemetry daemon | 11 | 11 | Rust 原生，需真機 |
| M1.2 breakpoint detection | 13 | 10 | |
| M1.3.1 VS Code ext | 6 | 6 | 需 extension host |
| M1.3.2 browser ext | 7 | 7 | 需瀏覽器 |
| M1.4 git telemetry | 7 | 5 | |
| M2.2 Gemma edge | 7 | 2 | 需 iPad / 本地 LLM |
| M2.3 Eguard | 8 | 1 | |
| M3.1–M3.6 | 6/9/8/9/5/5 | 全缺 | 前端已有 40 項 vitest 通過，但名稱與 SPEC 不同，需逐條對照 |
| M4.1 agent router | 22 | 14 | |
| M4.2 persona | 7 | 5 | |
| M4.3 role isolation | 9 | 9 | `testing/m4_3` 存在但名稱全不同 |
| M4.4 elicitation | 16 | 2 | |
| M6.2 PostgreSQL | 7 | 3 | |
| M6.3 role context | 5 | 4 | |
| M6.4 daily reflections | 7 | 2 | |
| M6.5 ACID gatekeeper | 9 | 2 | 與 RISK-01 有關，建議優先 |

`[進階]` 模組（M3.7–M3.11、M4.7、M4.8）不在 MVP 範圍，不列入待辦。M2.1 SPEC §6 沒有寫成測試函式。

---

## 3. 任務分類與本次已完成

### 🤖 AI 可自主完成

| 項目 | 狀態 |
|------|------|
| M0.2 sidecar skip marker | ✅ `test(m0.2)` |
| M6.1 `raw_content_stores` migration（只建立，未 apply 到任何真實 DB）+ 6 項 SPEC 驗收測試 + SPEC 範例補 `persona_id` | ✅ `feat(m6.1)` |
| `02_architecture.md` 配額表修正 | ✅ `docs(arch)` |
| GAP / DEVIATION 追蹤表與程式碼對齊 | ✅ `docs(gap)` |
| ruff `--fix`（83 項、21 個檔案；之後查過 F821/F823 未定義名稱：0） | ✅ `style` |
| 本報告 | ✅ `docs(review)` |
| M6.3 雲端 migration docstring 修正 | 未做（不改既有的 migration 歷史檔） |
| 純 Python 模組的缺漏驗收測試（M0.3、M0.4、M2.3、M4.4、M6.4、M6.5 等，每個缺 1–3 項） | 未做，下一輪優先 |
| ruff 剩餘 74 項 | 未做 |

### 👤 需要人類決策

依 CLAUDE.md「你必須詢問使用者的事」：研究約束鬆綁、跨模組職責邊界、`[進階]` 守門、需要真機的驗證。詳見 §4。

---

## 4. 留給人類的決策清單（依優先序）

**D1 🔴 隱私：逐字稿上雲（DEVIATION-09）**
- (a) 在 `02_architecture.md` 隱私表新增「使用者主動送出的對話訊息屬知情同意通道」豁免條款，並在送雲前對 `user_message` 與 history 都過一次 `EguardFilter.mask_pii()`。成本低，可以馬上做。
- (b) 不同意上雲時走回退路徑：雲端只看意圖向量 [R07: POST §4.3]，完整對話留在本地 LLM 生成回覆。需要先調查可行性與延遲。
- 建議：先做 (a) 的 `mask_pii`（不論最後選哪個都需要），(b) 列入研究項目。

**D2 🔴 MVP 閉環與 `[進階]` 硬依賴**
- 選項：(a) 現在產出 `MVP_CLOSURE_REPORT.md`，正式開放進階模組；(b) 先把 `m4_13` 路由改成可選載入（import 失敗或旗標關閉時略過），讓 MVP 能在移除進階模組後獨立啟動，再寫閉環報告。
- 建議：(b)。改動小，而且直接滿足「不要做的事 #7」。

**D3 🟡 trust_level 起始值（DEVIATION-08）**
- 選項：統一為 SPEC 的 0.5（隨互動升級），或改 SPEC 採用 0.7 / 0.8。改了之後 [R05] 注入率的驗收區間要一起調。

**D4 🟡 M4.4 confidence 資料來源（GAP-C3）**
- 選項：(a) M1.1 `TelemetrySegmentReport` 的分段信心；(b) M2.2 意圖向量的 confidence。決定後可以由 AI 實作並補測試。

**D5 🟢 M4.7 分級同步**
- `06_implementation_phases.md:81` 已記錄 2026-06-10 拍板移到 Phase 6。確認後把 `04_module_registry.md:653` 的 `[MVP]` 改成 `[進階]` 或註明「Phase 6」，並更新快速統計表的 M4 數字。

---

## 5. 測試結果

本機 Windows，2026-10-18，全部改動（含 ruff 修復）之後：

- 後端 `uv run pytest ../testing`：**472 passed / 0 failed / 13 skipped**（skip 含 6 項 M0.2 sidecar 測試與需要外部服務的測試）。修改前基線（雲端 run）：467 passed / 5 failed / 7 skipped，5 項失敗都是 sidecar 沒啟動。
- 前端 `pnpm test`（vitest）：**7 files / 40 tests 全過**。
- `ruff check .`：修復 83 項，剩 74 項需人工（見 §1 #12）；`--select F821,F823` 未定義名稱檢查：0。

---

## 6. 建議下一步

1. 拍板 D1 的 (a)，由 AI 補 `mask_pii` 與測試。
2. 拍板 D2，若選 (b)，由 AI 把進階路由改為可選載入。
3. 補 §2 中純 Python、不需外部服務的缺漏驗收測試（M6.5、M6.4、M4.4 優先，跟 RISK-01 和 R08 草稿核准機制有關）。
4. 新 migration `20261018_1000` 接在 `20260803_1100` 之後。若 `feat/m4-2-...` 之後又加了 migration，合併時要檢查是否出現多個 Alembic head。

---

## 7. 測試補齊（2026-10-18，第二輪）

**範圍**：§2 表中純 Python、不需外部服務的 MVP 模組。分支 `claude/wonderful-pare-7fa9d4`，以 fast-forward 接在 `claude/design-review-2026-10-18` 之後，每個模組一個 commit，未 push。

**做法**：逐一比對 SPEC §6 的 `def test_*` 與 `testing/`。名稱不同但行為已測到的不重複補；行為沒測到的才補。需要 sidecar、本地 LLM、Gemini key、Neo4j、Postgres 的測試一律 skip，不假裝通過。測到真 bug 就標 `xfail(strict=True)` 並寫明原因，不改設計；之後修好時 strict 會讓測試轉紅，提醒移除標記。

### 7.1 新增測試

| 模組 | SPEC 缺項 | 新增 | 結果 | commit |
|------|-----------|------|------|--------|
| M6.5 | `test_concurrent_settlement_safe` | 同名，用 `asyncio.to_thread` 並發結算（與 `main.py` 呼叫方式相同） | ❌ xfail（B1） | `test(m6.5)` |
| M6.5 | `test_gacha_atomic_deduct_and_reward` | 同名：扣費、開獎、ledger 三者一起產生且 ledger 指向該次獎勵；另補 `test_gacha_rollback_leaves_no_ledger_entry` | ✅ | `test(m6.5)` |
| M6.5 | （AC-2 的正式路徑） | `test_live_store_settles_approved_segment`：用 `main.py` 的 `LiveXPStore` 跑 AC-2 | ❌ xfail（B2） | `test(m6.5)` |
| M6.4 | `test_new_reflection_is_draft` | 同名：跑正式的 `AsyncDBAdapter.create_draft_reflection`，表結構取自 `main.py` 本身的 DDL | ✅ | `test(m6.4)` |
| M6.4 | `test_mood_score_range` | 同名：檢查本地 segments 表的 mood_score 範圍（Pydantic 層已有測試） | ❌ xfail（B3） | `test(m6.4)` |
| M4.4 | `test_daily_draft_generated_at_0200` | 同名：不注入 `today`，模擬 02:00 的系統時鐘（與 `draft_cron_loop` 的呼叫方式相同） | ✅ | `test(m4.4)` |
| M4.4 | `test_draft_uses_generalized_content` | 同名：用 `content_capture` 事件帶入 content_summary，檢查送雲用的 `*_generalized` 欄位 | ❌ xfail（B4） | `test(m4.4)` |
| M0.4 | `test_l1_payload_blocked_from_cloud` | 同名：`content_raw` 可留在本地 payload；`AsyncDBAdapter` 寫 `raw_tracking_logs` 時不碰雲端 engine | ✅ | `test(m0.4)` |
| M6.2 | `test_users_has_uuid_primary_key` | 離線版 `..._in_migration`：以紀錄用的 `op` 執行 cloud migration 的 `upgrade()`，檢查真正的 Column 物件；另有同名雲端版 | ✅ / ⏭ | `test(m6.2)` |
| M6.2 | `test_ai_experts_personality_prompt_max_length`、`test_xp_ledger_amount_must_be_nonzero` | 同名，雲端版。改用唯讀的 schema 查詢，不照 SPEC 範例 INSERT，因為 `SUPABASE_DB_URL` 可能指向正式專案 | ⏭ skip | `test(m6.2)` |
| M6.3 | `test_project_belongs_to_role`、`test_project_not_visible_across_roles` | 同名：透過 M4.3 `build_role_context` 讀取 `main.py` 本地 `role_projects`，附正向對照，避免空結果誤判通過 | ✅ | `test(m6.3)` |
| M6.3 | `test_role_delete_cascades_projects` | 同名，雲端版；整段包在一定會 rollback 的 transaction 裡 | ⏭ skip | `test(m6.3)` |

**名稱不同、行為已測到（不補）**

- M2.3 `test_injection_exception_carries_payload_hash_not_plaintext` → 已由 `testing/m2_3/test_eguard_filter.py::test_injection_exception_no_plaintext` 涵蓋（payload_hash 長度 64、例外字串不含明文）。
- M6.3 `test_implicit_state_scoped_by_role` → 已由 `test_implicit_state_scoped_by_user_and_role`（本地 SQLite）涵蓋。
- M6.5 其餘、M6.4 其餘：§2 的「缺」中，`test_acid_gatekeeper`、`test_ledger`、`test_daily_reflections` 等是 SPEC 檔名或註解裡的字串，不是測試名稱。

**刻意不補**

- M0.3 `test_missing_required_env_raises`：SPEC 要求缺 `GEMINI_API_KEY` 時拋 ValidationError，但 `services/config.py` 已定案「雲端 credential 全部 optional」，既有的 `test_settings_works_without_cloud_keys` 驗證的正是相反行為。這是 SPEC §6 過期，建議改 SPEC，不新增測試。

### 7.2 發現的 bug（全部 `xfail(strict=True)`，未改程式）

| # | 嚴重度 | 模組 | 問題 | 證據 |
|---|--------|------|------|------|
| B2 | 🔴 | M6.5 / M4.5 / `main.py` | **核准後的 XP 結算正式路徑會直接拋例外**。`LiveXPStore` 的 proxy 是 async（`get()`、`append()`），但 `XPGatekeeper` 同步呼叫它們，`settle_segment_xp()` 拿到的是 coroutine，在 `segment.is_active` 拋 `AttributeError`。`/api/m4_5/grant_xp` 因此回 500，XP 不會入帳。前端核准流程 `apps/desktop/src/components/m3_3_daily_report/DraftApproveModal/useApprovalGuard.ts:44` 呼叫的就是這支 | `services/main.py:2726-2763`、`:2853-2951`；`testing/m6_5/test_live_store_wiring.py` |
| B1 | 🔴 | M6.5 | **並發結算會重複發 XP**。`XPGatekeeper` 檢查 `xp_settled` 與寫入之間沒有鎖（SPEC §9 反模式第 2 條）。兩個 `asyncio.to_thread` 請求同時結算同一份反思，兩個都成功，XP 發兩次、ledger 兩筆。`/api/m6_5/grant_badge` 也是「先讀再寫」且 UPDATE 沒帶 `AND xp_settled = 0`，同樣有競態（閱讀程式碼確認，未另寫測試） | `services/m6_5_acid_gatekeeper/gatekeeper.py:85-147`；`services/main.py:2953-3020`；`testing/m6_5/test_acid_gatekeeper.py::test_concurrent_settlement_safe` |
| B4 | 🟡 | M4.4 | **RISK-15：送雲用的 `ai_description_generalized` 原文帶出 content_summary**。template 卡片（以及本地 Gemma 卡片）會在描述中引用 content_summary，而 `_eguard_generalize` 只呼叫 `EguardFilter.mask_pii`，只遮 PII 樣式、不做主題泛化，所以 generalized 欄位與本地欄位完全相同。目前沒有任何程式把這個欄位同步上雲，屬於潛在洩漏 | `services/m4_4_elicitation/draft_scheduler.py:36-46`、`gibbs_template.py:746-775`；`testing/m4_4/...::test_draft_uses_generalized_content` |
| B3 | 🟡 | M6.4 | **本地 `daily_reflection_segments` 沒有 `mood_score` 欄位**，1–10 範圍只在 Pydantic 層與雲端 migration。`PATCH /api/m6_4/reflections/{id}` 若帶 `mood_score`，SQLite UPDATE 會失敗，而 `AsyncDBAdapter.execute` 只記 warning 不往上拋，所以整筆更新（含 `is_reviewed`）會靜默遺失，API 仍回 `updated`（閱讀程式碼確認）。前端目前不送 `mood_score`，屬於潛在問題 | `services/main.py:900-924`、`:2683-2721`、`:198-238`；`testing/m6_4/test_local_store.py::test_mood_score_range` |

### 7.3 其他觀察

- **既有 RISK-15 測試是空轉的**：`testing/m4_4` 的 `test_draft_generalized_field_excludes_content` 與 `TestRisk15DualField::test_draft_stores_generalized_field` 把 `content_summary` 放在 `focus_session_ended` 的 payload，但 `group_signals` 只從 `content_capture` 事件讀 content_summary，所以這兩項沒有測到內文路徑。新測試已改用 `content_capture`。
- **M4.4 測試檔要跑約 170 秒**：既有的草稿測試沒有替換 LLM 主機，會等 `192.168.0.79` 與 Gemini 連線逾時。新測試用 `_no_llm()` 指向本機關閉的 port，每項約 2 秒。建議套用到其餘草稿測試。
- **02:00 排程本身測不到**：等待 02:00 的邏輯寫在 `main.py` lifespan 的閉包 `draft_cron_loop` 裡。新測試只涵蓋它的呼叫方式（不注入日期）。若要測時間計算，需要把「距下一個 02:00 的秒數」抽成函式。
- **M6.2 的約束只在雲端**：UUID 主鍵、`personality_prompt` 4096、`amount != 0` 都只寫在 cloud migration。`main.py` 實際寫入的本地 `users`、`ai_experts`、`xp_ledger` 表（TEXT id、無 CHECK）一項都沒有。是否需要在本地補 CHECK，取決於這些 L3 表是否長期以本地為主，留給人類判斷。
- **雲端測試未實際執行**：本機沒有 `SUPABASE_DB_URL`，新增的 4 項雲端測試（M6.2 ×3、M6.3 ×1）只確認會正確 skip，SQL 本身未在 Postgres 上驗證過。
- **ruff**：`services/` 執行 `uv run ruff check . --fix` 後沒有可自動修的項目，仍是 §1 #12 的 74 項。新增的測試檔都通過 `ruff check`。對 `testing/m4_4` 跑 `--fix` 時，順手移除了該檔兩個原本就未使用的 import；該檔另有 2 項舊問題（E501、F841）沒動。整個 `testing/` 還有 70 項可自動修的舊問題，分散在其他模組的測試檔，不在本次範圍。

### 7.4 測試結果

- 後端 `uv run pytest ../testing`：**480 passed / 0 failed / 17 skipped / 4 xfailed**（287 秒）。和第一輪基線 472 passed / 13 skipped 相比：+8 項新測試通過，+4 項新雲端測試 skip，4 項 xfail 即 B1–B4。
- 前端未改動，未重跑。
