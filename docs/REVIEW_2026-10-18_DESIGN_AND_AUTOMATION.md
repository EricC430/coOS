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
- **2026-10-18 進度：(a) 的 `mask_pii` 部分已實作**（使用者拍板）。
  - 新增 `services/m2_3_eguard/cloud_gate.py`，作為上雲前的統一遮蔽點。
  - 已接上 M4.2 `_call_gemini`（user_message + 16 條歷史）、M4.2 情節記憶與上次對話摘要（注入 system prompt 前），以及 M4.1 `_tool_ai_reply_gemini`（user_msg + 12 條歷史）。
  - 本地 L1 副本不動。遮蔽失敗即不上雲（fail closed）：persona 回 `None`，tool AI 回罐頭回覆，記憶改為不注入。
  - 有遮蔽時寫入 `raw_tracking_logs`（`M2.3` / `pii_masked_before_cloud`），payload 只記實體名稱與次數，不記內容。
  - 測試：`testing/m4_2/test_mask_pii_before_cloud.py`，8 passed + 1 xfail（見 D6）。
  - **尚未做**：`02_architecture.md` 的知情同意豁免條款文字。這是研究約束的鬆綁，要由使用者寫或確認措辭。

**D6 🔴 新發現：M2.3 PII 規則碰到中文就失效**
- `services/m2_3_eguard/patterns.py` 的 `TAIWAN_ID`、`CREDIT_CARD`、`IPV4`、`API_KEY_GOOGLE` 都用 `\b`。Python 把中文字視為 `\w`，所以中文字和英數字之間沒有 word boundary。
- 結果：`身分證A123456789`、`卡號4111111111111111` 這種中文使用者最常見的寫法**不會被遮蔽**，只有前面有空格或標點時才會。EMAIL 和 GENERIC_SECRET 不受影響。
- 已用 strict xfail 測試記錄（`TestKnownEguardGaps`）。修好後該測試會變成 XPASS 而報錯，提醒拿掉 xfail。
- 選項：(a) 把 `\b` 改成 `(?<![A-Za-z0-9])` / `(?![A-Za-z0-9])`，只看英數字邊界。可能讓中文裡的長數字串（時間戳、訂單號）被誤判為卡號，需要補 Luhn 檢查降低誤判；(b) 維持現狀，在文件註明限制。
- 建議：(a) 加 Luhn。這會改變 M2.3 的遮蔽行為，所以需要拍板。
- **2026-10-19 進度：已依 (a) 修正**（使用者拍板）。
  - `patterns.py`：TAIWAN_ID、CREDIT_CARD、IPV4、API_KEY_GOOGLE 與 LOCALHOST_PATTERN 改用英數字邊界 lookaround。
  - `filter.py`：卡號候選須通過 Luhn 才遮蔽。
  - M2.3 SPEC 升為 v1.2。
  - 測試：`testing/m2_3/test_eguard_cjk_boundaries.py` 新增 15 項；`test_mask_pii_before_cloud.py` 的 xfail 已轉為正式測試。
  - 保留原有行為：`XA123456789`、`v1.2.3.4` 仍不遮蔽；code context 的 `127.0.0.1` 仍略過。
  - 已知取捨：Luhn 隨機通過率約 10%，所以中文句子裡的 13–16 位數字串仍有少量誤判；遮蔽寧多勿少，可以接受。

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

1. ~~拍板 D1 的 (a)，由 AI 補 `mask_pii` 與測試。~~ 已完成（見 D1 進度）。D6 也已修正（2026-10-19）。
2. 拍板 D2，若選 (b)，由 AI 把進階路由改為可選載入。
3. 補 §2 中純 Python、不需外部服務的缺漏驗收測試（M6.5、M6.4、M4.4 優先，跟 RISK-01 和 R08 草稿核准機制有關）。
4. 新 migration `20261018_1000` 接在 `20260803_1100` 之後。若 `feat/m4-2-...` 之後又加了 migration，合併時要檢查是否出現多個 Alembic head。
