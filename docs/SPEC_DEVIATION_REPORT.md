# SPEC 偏離報告 (Spec Deviation Report)

**日期**：2026-06-10
**範圍**：Phase 4/5 期間的手動修改（含未 commit 的 working tree 變更）與既有 SPEC 文件的不一致清單
**用途**：每一條需逐項拍板——**「更新 SPEC 接受新行為」或「回退程式碼遵守 SPEC」**，二擇一。拍板前該行為視為未定案。

> 標記說明：
> - 🔴 違反 SPEC 明文鐵則 / 研究約束，預設應回退，除非使用者明確拍板鬆綁
> - 🟡 行為偏離 SPEC 但有合理產品動機，建議更新 SPEC
> - 🟢 屬 bug 修正或向 SPEC 靠攏，僅需補文件

---

## DEVIATION-01 🔴 M4.4 套問頻率鐵律被放寬

| | |
|---|---|
| SPEC | `M4_4_natural_elicitation_draft_SPEC.md` §5 / §7：「每次對話最多套問 **1** 次；cooldown 至少 **5** 個 turn」（防「被審問感」） |
| 現況 | `services/m4_4_elicitation/controller.py:96-99`：`MAX_PER_THREAD = 3`、`COOLDOWN_TURNS = 2`；另新增 `goal_probe` / `deadline_probe` 模板與 main.py 中的輪替注入 |
| 後果 | `testing/m4_4` `test_elicitation_cooldown` 失敗；R08 微干預原則的風險緩解失效（套問過密 → 使用者防衛） |
| 附帶偏離 | SPEC §5 要求「`TelemetrySegmentReport.confidence ≥ 0.7` 的時段不觸發套問」——main.py 注入路徑**完全沒有接這個檢查**；且套問訊息以 `reply += "\n\n..."` 黏在同一則回覆，違反 SPEC §7 `inject_messages` 多氣泡設計 |
| 建議 | 若產品需要多輪套問（目標/截止日探詢），改成「**每個 context 類型各 1 次**、總量 ≤ 3、cooldown 維持 ≥ 3 turn、補 confidence 檢查」並同步改 SPEC + 測試；否則回退 |

## DEVIATION-02 🟡 M4.1 路由圖結構與 SPEC 不同

| | |
|---|---|
| SPEC | `M4_1_agent_router_SPEC.md` §7 + 原 graph.py：`confidence_branch`（high/mid/low 三路）、獨立 `llm_router` 與 `observer_dispatch` 節點 |
| 現況 | `services/m4_1_router/graph.py`：線性圖 `drift_guard → rule_router → persona_container → END`；信心分層內聚於 `route_with_confidence()`；Observer 改 `asyncio.create_task` 背景派發；新增 `frontend_explicit` 短路 |
| 評估 | 功能等價且降低回應延遲，屬合理重構 |
| 建議 | 更新 SPEC §7 圖示與節點清單，標注「Observer 非同步派發不佔 graph 邊」 |

## DEVIATION-03 🟡 工具型 AI 行為大改：罐頭 → Gemini 真實對話 + 配對建議

| | |
|---|---|
| SPEC | M4.1/M3.4 SPEC 中工具型 AI 僅為「無人設的預設回應容器」；配對僅由使用者主動發起（`[配對]` 按鈕） |
| 現況 | `graph.py::_tool_ai_reply_gemini()`：帶 6 輪歷史的真實 LLM 對話、`[SUGGEST_MATCH]` 標記 → 前端顯示配對建議橫幅（混合主動式觸發） |
| 評估 | 與 [R08 §一 混合主動式] 精神一致，且 M3.4 SPEC 本就有「AI 幫手聊天時的推薦通知」解鎖路徑，屬正向擴充 |
| 建議 | 在 M3.4 SPEC §7 增補「AI 主動配對建議」流程圖與 `suggest_match` API 欄位定義 |

## DEVIATION-04 🟡 M3.4 點擊側欄專家直接切換聊天室

| | |
|---|---|
| SPEC | `M3_4_multi_agent_helper_SPEC.md`：「**不允許直接點擊尚未配對解鎖的 Persona 開啟對話**」+ 驗收測試「直接點選清單中的 Persona 無法啟動對話，必須透過配對流程」 |
| 現況 | `ExpertSidebar/index.tsx`：點擊**已解鎖**專家直接切換到該專家的獨立聊天室（`thread_{roleId}_{expertId}`） |
| 評估 | 語意上不衝突——側欄只顯示已配對解鎖的專家，「未解鎖不可點」的前提仍成立；但 SPEC 驗收測試的字面描述會 fail |
| 建議 | 更新 SPEC 驗收測試為「未解鎖專家不出現在側欄；已解鎖專家點擊 = 切換聊天室」，並補「每專家獨立 thread」的 thread_id 命名規範 |

## DEVIATION-05 🟡 配對成功後專家主動發問候語（且跳過預覽確認）

| | |
|---|---|
| SPEC | M4.1 §7.5 配對流程狀態機：「rule 比對 → LLM 新建 → **使用者預覽確認**」；[R09 §第四章 SDT]「讓使用者感到是我選的」 |
| 現況 | `match_persona` 直接生成專家 + 寫入 DB + 回傳 hardcoded 問候模板（依 tone 三選一）；前端直接進入對話，**無預覽確認步驟** |
| 後果 | (a) SDT 自主感削弱；(b) 問候語是寫死模板而非 persona 語氣（破壞 [R03 §1] 人設一致性）；(c) 問候語**未寫入 chat_transcripts**，重新整理後消失 |
| 建議 | 保留「專家先開口」體驗（好），但問候語改由 M4.2 graph 以 persona 語氣生成並落地 transcripts；預覽確認可簡化為問候氣泡上的「換一位」按鈕（rematch），需在 SPEC 拍板 |

## DEVIATION-06 🟡 M4.6「專案偵測」語意改為「主題標籤 (Topic Tag)」+ LLM 回退

| | |
|---|---|
| SPEC | `M4_6_observer_agent_SPEC.md` §7.2 以「專案」為實體；§9 有 LLM 回退決議但未定義三段式流程 |
| 現況 | `project_detector.py`：Regex 快速路徑 → 既有標籤模糊比對 → LLM 語意分析（Gemma → Cloud fallback）→ Eguard → 去重 → upsert；docstring 已聲明「專案＝聊天主題標籤」 |
| 後果 | `testing/m4_6` 3 個測試失敗（FakeDB 介面 + fuzzy 行為改變） |
| 建議 | 更新 SPEC §7.2 定義 Topic Tag 語意與三段式流程；更新測試的 FakeDB 補 `fetch_all`/`execute` |

## DEVIATION-07 🔴 RoleIsolationMiddleware 新增豁免路徑繞過 RISK-06 驗證

| | |
|---|---|
| SPEC | `M4_3_role_isolation_SPEC.md` §7.1：所有 `/api/m4_*` 需驗證 role 所有權 |
| 現況 | `middleware.py:26-28` 新增 `/api/m4_1/history`、`/api/m4_1/threads`、`/api/m4_1/match_persona` 至 EXEMPT_PATHS。`history` 端點可用任意 `role_id` query 拉取**任何角色的對話逐字稿**，無所有權驗證 |
| 後果 | 單機單使用者下風險低，但違反 RISK-06 縱深防禦；未來 L3 多裝置同步時成為漏洞 |
| 建議 | 移出 EXEMPT_PATHS，改讓這三個端點走正常驗證（它們都有 role_id 參數，中介軟體本就支援 query param 提取）——不應豁免，應是當初為了繞 422 而加，需查明後修正 |

## DEVIATION-08 🟡 M4.2 預設 tone / trust_level 變更

| | |
|---|---|
| SPEC | `M4_2_persona_state_machine_SPEC.md` §9 決議：trust_level 起始 **0.5**；fallback tone 原為 `authoritative` |
| 現況 | `m4_1_router/graph.py` fallback expert 與 persona_input 預設改為 `empathetic` / `0.7`；`_ai_generate_expert` 寫入 DB 的 trust_level 固定 **0.8** |
| 後果 | [R05 §跨越恐怖谷] 副語言注入率公式 `0.08 × (1.5 − trust)` 隨之變化（0.5→8%、0.8→5.6%），SPEC 驗收測試的 6%~10% 區間假設不再成立 |
| 建議 | 拍板新起始值（建議：自動生成專家 0.5 起跳，隨互動升級），同步修 SPEC §9 與驗收區間 |

## DEVIATION-09 🔴 Persona 對話逐字稿（L1）直送雲端 Gemini —— 隱私三層原則張力點

| | |
|---|---|
| 憲章 | CLAUDE.md 隱私三層：「對話逐字稿 = L1，**絕對不上雲**」；不要做的事 #2：「不要讓 cloud LLM 看到對話逐字稿，任何上雲呼叫必須先經 M2.2.2 + M2.3」 |
| 現況 | `m4_2_persona/graph.py::_call_gemini` 與 `_tool_ai_reply_gemini` 將 user_message + 最多 16 條逐字稿歷史直接送 Gemini API。僅經 DRIFT 注入檢查，未經意圖向量壓縮或 Eguard PII 遮蔽 |
| 評估 | 對話式 AI 不把訊息給 LLM 就無法回應——此為架構必然。但憲章字面禁止，且**歷史訊息未過 Eguard mask_pii** 是可以補的 |
| 建議 | 需使用者拍板：(a) 在 `02_architecture.md` 隱私表新增「使用者主動發送之對話訊息屬知情同意通道」豁免條款；(b) 無論如何，送雲前對 user_message 與 history 過一次 `eguard.mask_pii()`（成本極低） |

## DEVIATION-10 🟢 種子/示範資料移除（向真實資料靠攏）

`main.py`：`daily_timeline` 不再回傳「微積分作業」demo 卡片（改回 `[]`）；`role_context` 不再塞假承諾/目標；SSE `/api/m4_6/events` 從「3 秒後固定吐『期末考準備』假事件」改為真實廣播 + PING keepalive；角色名稱不再 hardcode「CSIE」。**正向**，僅需確認前端空狀態 UI 不破版。

## DEVIATION-11 🟢 SQLite 布林相容性與欄位修正

`is_active = TRUE` → `= 1`、`inferred_by_ai` 同理；殭屍清理 `is_approved` → `is_reviewed`（schema 實際欄位名）。屬 bug 修正。

## DEVIATION-12 🟡 文件端：`02_architecture.md` Gemini 配額表有錯置

新增的 Free Tier 配額表中 `Gemma 4 26B` 出現兩列（RPM 15 / 31），疑似第二列應為 `Gemma 4 31B`；且表格縮排在部分 Markdown renderer 會破版。需修正。

---

## 拍板追蹤表

| 編號 | 等級 | 決議 (擇一) | 狀態 |
|------|------|-------------|------|
| DEVIATION-01 | 🔴 | 每個 context 類型各 1 次、總量 ≤ 3、cooldown 維持 ≥ 3 turn、補 confidence 檢查」並同步改 SPEC + 測試 | ■ 已拍板 |
| DEVIATION-02 | 🟡 | 更新 SPEC | ■ |
| DEVIATION-03 | 🟡 | 更新 SPEC | ■ |
| DEVIATION-04 | 🟡 | 更新 SPEC + 測試 | ■ |
| DEVIATION-05 | 🟡 | persona 化問候 + 落地 transcripts + 仍要保留舊的系統配對的預覽確認(因為它其實是系統要跟使用者確認，是否要跟這個專家配對) | ■ |
| DEVIATION-06 | 🟡 | 更新 SPEC + 修測試 | ■ |
| DEVIATION-07 | 🔴 | 移出豁免清單 | ■ |
| DEVIATION-08 | 🟡 | 拍板 trust 起始值 | ■ |
| DEVIATION-09 | 🔴 | 隱私條款拍板 + 補 mask_pii + 不同意隱私條款的回退手段:使用意圖向量在CloudLLM收集可能的資訊再綜合對話完整內容與資訊在LocalLLM生成回應以及其他人設語氣等後處理(要調查最佳實踐、可行性與否) | ■ |
| DEVIATION-10/11 | 🟢 | 補文件即可 | ■ |
| DEVIATION-12 | 🟡 | 修配額表 | ■ |
