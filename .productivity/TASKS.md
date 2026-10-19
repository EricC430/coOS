# Tasks

> 範圍：**只有 coOS Phase 1（底層接通）**。
> 生活與學業任務仍以 Obsidian Vault 為唯一真相（`Executive/Projects`、`Routines`、Daily note 的 Time Blocking）。
> 依據：`docs/PHASE1_SCOPE_AND_ACCEPTANCE.md`

## Active

### W0 — 開工前拍板（六題，全部答完才進 W1）

- [ ] **D1 分層架構是否入憲** - Vault = Layer 0 底層；所有模組設計的前提
- [ ] **D2 等級公式統一為哪一套** - 全域 `floor(0.1·√XP)` vs 技能 `floor(√(XP/100))+1`；不定案則劇本步驟 8 無法驗收
- [ ] **D3 `.coos_inbox/` 落地是自動還是手動** - 手動（QuickAdd 按一下）＝多一道心理所有權關卡，但多一次摩擦
- [ ] **D4 行內標記語法** - `[coos:: id]`（可查詢可撤銷但會顯示）vs `<!-- coos:id -->`（隱形但撈不到）
- [ ] **D5 垂直切片十一步是否就是你要的第一階段** - 最重要的一題；有沒有哪步不重要、或漏了關鍵的一步
- [ ] **D6 是否同時做 N=1 證據報告** - 或只做基線量測；影響 W0 與 W4 工作量

### W0 — 想像外化四件套（完成前不准寫實作程式碼）

- [ ] **逐字劇本 DEMO_SCRIPT.md** - `docs/phase1/`；第一人稱、含實際字串、含「不該發生什麼」
- [ ] **黃金樣本 testing/golden/phase1/** - 5 份：daily savepoint / skill xp 行 / inbox 靈感行 / role 匯入物件 / 草稿卡欄位
  - 鐵則：**不得由 AI 生成或修改**
- [ ] **反例清單 ANTI_EXAMPLES.md** - 從 `docs/manual_test_log.md` 萃取成可測斷言
- [ ] **基線量測 BASELINE.md** - 動工前先跑：Vault 衰減曲線 / 草稿核准率 / 每日互動分鐘數 / 冷啟動空白程度

### W1 — 文件入憲 + M4.7a Reader（劇本步驟 1、2、9）

- [ ] **`02_architecture.md` 新增 Layer 0** - 並在 §3 隱私表加「Vault = L3-local」列與 L1 例外
- [ ] **`01_product_vision.md` 改寫「不是什麼」第二條** - 「不存內容」→「不擁有內容的所有權」
- [ ] **`04_module_registry.md` 把 M4.7 拆為 a / b / c**
- [ ] **`CLAUDE.md` 新增 Phase 1 三條鐵則** - 黃金樣本 AI 不得動 / AI 不得宣告 L2 通過 / 寫入 Vault 必經 `.coos_inbox`
- [ ] **M4.7a Vault Governance Reader** - 唯讀 + 週期重掃，不做一次性 import
  - Roles / Domains / Skills / Principles / Projects / `active_period`
  - 可先用 Obsidian MCP 手動模擬一次再決定寫不寫程式

### W2 — M4.7c 事件匯流排（步驟 6 骨架 + 步驟 11）

- [ ] **`_System/.coos_inbox/` 與 `.coos_outbox/` 契約定義**
- [ ] **`applyCoosInbox.js`** - 含建檔防呆（今日日記不存在）與建區塊防呆（模板改版）
- [ ] **驗證 coOS 關閉時 Vault 獨立運作** - QuickAdd 6 個巨集 + iOS 捷徑全部可用

### W3 — M4.7b Writer + 冪等去重（步驟 6、7、8、10）

- [ ] **Daily note Save Point 區塊回寫** - append-only、帶 `coos::`、核准後才寫
- [ ] **Skill note Experience Log 回寫** - 格式完全遵守 `logSkillXP.js` 慣例
- [ ] **冪等重放保護** - 同 id 重放 3 次，Vault diff 為空
- [ ] **`possible_duplicate` 詢問流程** - 人工 claim 與 coOS 回寫撞號時問使用者，不自動合併

### W4 — 驗收

- [ ] **L1 契約檢查自動化（8 條）** - 見 `PHASE1_SCOPE_AND_ACCEPTANCE.md` §3.1
- [ ] **L2 保真判定** - 照劇本走 11 步，逐項與黃金樣本 diff，填判定表
- [ ] **L3 體感記錄啟動** - 連續 7 天，每天 3 個數字
- [ ] **`CLOSURE_REPORT_PHASE_1_SUBSTRATE.md`** - 主要成果陳述必須是 L2 判定表，不得是「N passed」

## Waiting On

- [ ] **MCP 授權（若要用）** - GitHub / Notion / Linear 等尚未授權，非 Phase 1 必要
- [ ] **Vault 自身待修項** - `Governance/Visions` 是空的、`00 Inbox` 死查詢；D2 等級公式須在 Phase 1 前定案，其餘可自行排

## Someday

> 停車場。新想法一律先進這裡，附「如果現在不做會怎樣」。答案是「不會怎樣」就留著。

- [ ] **coOS 端快速捕捉筆記** - 路徑已設計（`docs/DESIGN_PHILOSOPHY_AUDIT.md` §3.7.4），依賴 M4.7c 穩定；排 Phase 2 第一項
- [ ] **M1.7 摩擦預算控制器** - 需 Phase 1 基線數據才知道門檻設多少
- [ ] **人生階段 Period 一級概念** - Phase 1 只讀出 `active_period` 並顯示，不改心理參數
- [ ] **Persona 語氣硬約束** - 問候 ≤40 字、一氣泡一問題、延遲 = f(字數, WPM)
- [ ] **「今日一張卡」UI 收斂**
- [ ] **輕量冰山 M5.1** - `m5_1_iceberg_claims` + 符號驗證 + `user_confirmed`
- [ ] **Gibbs 模板對齊底層五段式** - 補「突觸連結」段
- [ ] **專案健康度回報** - 偵測 30 天無遙測的 Project → 提議降 `on_hold`

## Done

- [x] ~~設計哲學稽核報告~~ (2026-08-08) - `docs/DESIGN_PHILOSOPHY_AUDIT.md`
- [x] ~~互動式視覺化~~ (2026-08-08) - `docs/DESIGN_PHILOSOPHY_AUDIT.html`
- [x] ~~Phase 1 範疇與驗收契約~~ (2026-08-08) - `docs/PHASE1_SCOPE_AND_ACCEPTANCE.md`
