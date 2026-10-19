# add-m0-5-gemini-free-tier-guard:M0.5 合成使用者的 Gemini 呼叫只用免費額度,並以可設定的配額守門員強制

**狀態**:`implementing`  <!-- proposed → approved → implementing → done → archived -->
**Track**:`T3 New Module` (M0.5 SPEC 為 `draft`,直接修改 SPEC 本身,不另寫 delta)
**模組**:`M0.5`
**標籤**:`[測試基礎設施]`
**分支**:`feat/add-m0-5-gemini-free-tier-guard` (建議;目前仍在 `feat/m4-2-episodic-memory-m4-6-topic-anchors` 工作區,未提交)
**提出**:2026-10-19 **拍板**:2026-10-19 (使用者原話:「Gemini monthly spending cap 目前 (做成可配置) 只使用免費用戶額度,查清楚最新限額並腳本化」)

## Why (為什麼要改)

M0.5 SPEC §9.2 Q8 (Gemini 月金額上限) 未決。使用者決定只用免費額度,但要可設定、限額要查證並寫成腳本。查證發現 Google 已不公布逐模型免費額度表 (改為依專案在 AI Studio 顯示),而原 SPEC 估計的每輪約 10,000 次呼叫在免費額度下需約 41 個真實天數,不可行。

## What Changes (改什麼)

- 新增配額守門員 `services/m0_5_synthetic_sim/quota/`:`mode = off | free_only (預設) | paid_capped`;依 RPM / TPM / RPD (太平洋午夜重置) 與「專案額度分配比例」放行或拒絕;被拒時改用 TemplateRealizer。
- 從 Gemini 429 的 `QuotaFailure.quotaValue` 學到實際限額並寫入合成庫 `m0_5_quota_ledger`;`free_only` 下看到非 FreeTier 配額 → 鎖住所有雲端呼叫。
- CLI:`status`、`plan`、`clear-paid-latch`。
- 新增共用隔離工具 `m0_5_synthetic_sim/isolation.py` (路徑拒絕 + `application_id` 哨兵,RISK-24)。
- SPEC 改動:§7.4.1 (新)、§7.8 (每輪改為每人日 1 次批次呼叫,約 874 次 / 約 4 天)、§9.1 Q8–Q11 拍板、§9.2 新增 Q12 (雲端 Gemma 4 作為消融對照)。
- 無 BREAKING:未改任何既有模組、API、正式 schema。

## Impact (影響)

| 類型 | 項目 |
| ---- | ---- |
| 受影響 SPEC | `docs/modules/M0_5_synthetic_user_simulator_SPEC.md` (draft,直接修改) |
| 程式碼 | `services/m0_5_synthetic_sim/{__init__,isolation}.py`、`services/m0_5_synthetic_sim/quota/*` |
| 測試 | `testing/m0_5/test_quota_guard.py` (24 個) |
| API | 無 |
| 資料表 / migration | 只在 `data/coos_synthetic.db` 建 `m0_5_quota_ledger` (`CREATE TABLE IF NOT EXISTS`,非 Alembic;不碰正式庫) |
| 文件 | `05` RISK-24 已有,不需更新;`04` 尚未登錄 M0.5 (另案) |

## 研究依據

無 (工程 / 營運決策)。

## 整合風險 (audit-integration 結果)

- **觸及模組**:M0.5 (只此一個;M0.3 `Settings` 僅被讀取以取得正式庫路徑)
- **觸發的 RISK**:
  - `RISK-24` 合成污染 — 緩解:本 change 實作 → `test_sqlite_ledger_refuses_real_db`、`test_sqlite_ledger_rows_synthetic_and_sentinel`、`test_sqlite_ledger_refuses_foreign_db`
- **未觸發但相關**:`RISK-19` (M0.5 雲端呼叫只帶合成資料;被測模組路由不變)
- **新發現的風險**:免費層內容會被 Google 用於改進產品 → 若 coOS 正式 app 也走免費層 key,真實對話 (已遮罩) 會受此條款約束。屬 M4.1 / M4.2 範圍,未新增 RISK,列為 SPEC §9.2 Q10 交使用者決定。

## 憲章檢查

- [x] 不涉及 L1 明文上雲 (只送合成資料)
- [x] 不自動核准草稿、不繞過 XP 守門
- [x] 不移除微摩擦
- [x] MVP 不硬依賴進階模組 (正式程式碼沒有 import `m0_5_synthetic_sim`)
- [x] 上雲金流設定:預設零花費;改為付費需使用者手動改設定檔並填上限

## Out of Scope (本 change 不做)

- realizer 本身 (Gemini 呼叫、批次 prompt) —— 之後實作 M0.5.3 / realizer 時接上 `QuotaGuard`
- M4.1 `routing_engine._GeminiRateLimiter` 的限額 (正式 app;不同 change)
- 在 Google 端建立新專案 / 金額警示 (使用者操作)

## 後續 (實作中發現、留給之後的 change)

- `04_module_registry.md` 登錄 M0.5
- 正式 app 的 Gemini key 層級與資料條款檢查 (Q10)

## 拍板項

- 拍板:只用免費額度,做成可設定,限額查證並腳本化 (2026-10-19)
- 拍板:Q9 先共用同一把 key,`share_of_project_quota` 維持 0.5 (2026-10-19)
- 拍板:Q10 coOS 正式對話目前也先用免費層 key (2026-10-19)
- 拍板:Q11 使用者提供 AI Studio 實際限額,已寫入設定並 `verified = true`;備援模型改為 `gemini-3.5-flash-lite` (2.5 Flash-Lite 只有 20 RPD) (2026-10-19)
