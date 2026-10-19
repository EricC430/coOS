# 開發流程稽核 (Dev Process Audit)

**日期**:2026-10-19
**範圍**:會影響 AI (Claude Code) 開發行為的高階文件、範本與提示詞——`CLAUDE.md`、`.claude/skills/{implement-module, audit-integration, cite-research}`、`docs/00_README.md`、`docs/modules/_TEMPLATE_SPEC.md`、`docs/06_implementation_phases.md`、CI 設定,以及它們在 git 歷史與報告中留下的後果。
**結論**:領域規則 (隱私三層、研究約束、整合風險、模組編號) 品質很好,應保留;問題集中在**流程**——沒有「變更」這個單位、完成定義停在單元測試、多份文件寫死會過時的事實、以及在錯的地方要求確認。
**處置**:新增 `docs/DEV_WORKFLOW.md` 作為流程唯一權威,`CLAUDE.md` 改為憲章 + 路由,新增 `propose-change` / `archive-change` skill 與 `docs/changes/` 範本,修正其他 skill 與範本。

> 嚴重度:🔴 會讓 AI 產出錯誤結果 🟡 造成漂移或返工 🟢 冗贅 / 浪費 token

---

## A. 正確性問題 (AI 照做會出錯)

### A1 🔴 skill 與憲章寫的路徑不存在

| 文件 | 寫的 | 實際 |
| ---- | ---- | ---- |
| `implement-module` Step 4 | 後端測試 `tests/m{x}_{y}/` | `testing/mx_y/` (`pytest.ini` `testpaths = testing`) |
| `implement-module` Step 4 | 前端測試 `apps/web/src/components/m{x}_{y}/<name>.test.tsx` | `apps/desktop/tests/mx_y/` |
| `CLAUDE.md` 命名範例 | `apps/web/src/components/m3_2_dashboard/` | `apps/desktop/src/components/m3_2_dashboard/` |

**後果**:照 skill 建的測試不會被 pytest 收集,出現「沒有失敗 = 通過」的假綠燈。同一個混淆也讓 `IMPLEMENTATION_GAP_REPORT.md` GAP-A2 誤判「前端 0 個測試」(`MVP_CLOSURE_REPORT.md` §2.2 已更正:測試在 `apps/desktop/tests/`,40 個通過)。
**處置**:`CLAUDE.md` 新增「專案地圖」並宣告它優先於 skill;`implement-module` 改寫路徑,並要求 Red 階段確認測試「真的被收集到」。

### A2 🔴 測試指令與 CI 涵蓋範圍不可靠

- 根目錄 `package.json` 的 `pnpm test` 執行 `uv run --directory services pytest testing/`——路徑解析為 `services/testing/`,**該目錄不存在**。
- `.github/workflows/ci.yml` 後端只跑 `testing/m0_1/` 與 `testing/m0_3/`,也就是 25 個測試目錄中的 2 個;其餘 458 個測試的回歸不受 CI 保護。
- 舊 `CLAUDE.md` 建議 `pytest -v 2>&1 | tail -20`,未指定 venv;系統 Python (Anaconda) 缺 langgraph 等套件 (見 `feedback_patterns` 記憶),會得到 ImportError。

**處置**:`CLAUDE.md`「常用指令」改為已驗證的 `services/.venv` 指令,並標註 `pnpm test` 目前損壞。**未修**:`package.json` 與 `ci.yml` 屬程式 / 基礎設施變更,列為後續 (§E)。

### A3 🔴 寫死的事實已過時,AI 會信以為真

| 位置 | 寫死內容 | 現況 |
| ---- | -------- | ---- |
| `docs/00_README.md` | 「10 篇研究」「12 條已知陷阱」 | R01–R26、RISK-01–25 |
| `docs/00_README.md` | 列出 `M0_infrastructure_SPEC.md`、`M4_agents_SPEC.md` 等 8 份檔案 | 皆不存在;實際為 45 份 `Mx_y_*_SPEC.md` |
| `docs/00_README.md` | `RISK-03 = Echo Mode + ARPM 衝突` | 那是 RISK-02;RISK-03 是焦慮鏡像 |
| `audit-integration` 速查表 | 止於 RISK-23 | RISK-24/25 (M0.5) 已存在 |
| `cite-research` | 「只有 R01-R26」(先前版本為 R01-R10) | 每次新增研究都要手改 |

**處置**:改成「grep 現查」;速查表保留但標明「僅供提示,以 grep 為準」並補 M0.5 列;`00_README.md` 重寫。

### A4 🔴 SPEC 狀態欄位失效

`_TEMPLATE_SPEC.md` 的版本欄位寫成 `` `1.0` / `draft` `` (兩個選項並列),14 份 SPEC 原樣照抄,至今仍是 `1.0 / draft`——無法判斷哪些 SPEC 已定案。範本 §7 底下的小節編號又寫成 6.1~6.3。
**處置**:範本拆成 `狀態` (draft / approved / implemented / deprecated,單選) 與 `版本` (semver),新增 `最後變更: <change-id>` 與變更紀錄表;修正小節編號。既有 SPEC 不批次改寫 (漸進遷移,見 DEV_WORKFLOW §10)。

### A5 🟡 守門條件在憲章與程式碼間描述不一致

舊 `CLAUDE.md`「不要做的事 #6」只寫「缺少 `is_draft = false` 確認前不發 XP」;實際 `services/m6_5_acid_gatekeeper/gatekeeper.py:109-120` 要求 `is_draft=False` **且** `is_reviewed=True` **且** `user_feeling`、`user_action_plan` 非空 **且** 未 `xp_settled`。只照憲章實作會漏三個條件。
**處置**:憲章第二條改為完整條件。

### A6 🟡 進階模組守門條件是「檔案存在」

舊規則:「`[進階]` 模組必須等 … 產出 `docs/MVP_CLOSURE_REPORT.md` 後才能進入」。該檔已存在,但其 §7 判定為 **NO-GO (條件式)**。照字面,進階模組已可動工。
**處置**:憲章第五條改為「最新判定為 GO」。

---

## B. 流程缺口 (造成 SPEC 漂移與返工)

### B1 🔴 沒有「變更」這個工作單位

唯一的工件是 SPEC,改行為時沒有提案 / 差異 / 歸檔機制,所以實務上是**先改程式碼,事後在報告補登**:

- `SPEC_DEVIATION_REPORT.md` DEVIATION-01 🔴:M4.4 套問上限從 1 改為 3、cooldown 從 5 改為 2,沒有走拍板,導致 `test_elicitation_cooldown` 失敗、R08 緩解失效。
- 同報告共 13 條偏離、`IMPLEMENTATION_GAP_REPORT.md` 有 A~D 四類缺口,都是事後清點出來的。

兩份報告本身是好的稽核工具,但它們的存在說明流程**在事前沒有攔住**。
**處置**:引入 OpenSpec 式 `docs/changes/<change-id>/` (proposal + spec delta + tasks),憲章第三條「規格即合約:不留程式碼與 SPEC 不一致的狀態」。兩份報告改為只登記「既存」落差,每條以一個 change 關閉。

### B2 🟡 沒有需求釐清階段

`implement-module` 從「讀 SPEC」直接進「寫測試」。SPEC 範本 §9 要求「至少 1 個開放問題 (沒有 → 思考不足,重來)」,卻沒有任何步驟要求在寫程式前把問題拍板——結果是鼓勵**製造**問題,而不是**解決**問題。
**處置**:DEV_WORKFLOW P1 (Superpowers brainstorming / Spec Kit clarify):一次問一個問題、2~3 方案附建議;`[NEEDS DECISION]` 最多 5 個且 G1 前必須清空;範本 §9 改為「沒有問題就寫無」。

### B3 🟡 沒有計畫 / 任務拆解

從測試直接跳到實作,大模組 (例:M4.2 SPEC 約 250 行) 一次完成。git 歷史中後期 commit 粒度失控:`frontend patching`、`until MVP manual testing 3`、`readme updates`、`rest updated commit`,無法對應到任何 SPEC 或需求。
**處置**:P3 `tasks.md`——每個任務 = 一個測試 + 最小實作、寫明檔案路徑與 Red 指令;加上 Spec Kit `/analyze` 式一致性表 (需求情境 ↔ 任務 ↔ 測試、RISK ↔ 標記測試)。

### B4 🔴 「完成」只定義到單元測試綠燈

專案記憶與 `MVP_CLOSURE_REPORT.md` §9.2 記錄了單元測試全綠、接縫卻是壞的:

- `/api/m4_5/grant_xp` 一直回 500 (同步 `XPGatekeeper` 包非同步 `LiveXPStore`)
- XP 寫入靜默失敗 (`AsyncDBAdapter.execute` 吞掉不存在欄位的錯誤)
- `from config import settings` 錯誤導致 cron 對話壓縮靜默停用

`services/main.py` 中以 grep 粗估約 25 處 `except` 後直接接 `pass`。
**處置**:P5 驗證 (Superpowers verification-before-completion):新鮮證據才可宣稱完成、跨模組必須閉環測試、使用者可見改動要實際打 endpoint;憲章第七條禁止靜默吞例外。

### B5 🟡 Bugfix 沒有根因流程

舊 `implement-module`:「bugfix 只用 Step 6-7」(反覆跑測試 + commit)。歷史中可見猜測式修正:`d9c7a1e git and github webhook repairement` → `de33df1 github webhooks errors repairment` → `4050174 github webhook frontend repairment` 連續三個 commit 修同一區。
**處置**:DEV_WORKFLOW §5 (Superpowers systematic-debugging):重現 → 蒐證 (`raw_tracking_logs`) → 單一假設驗證 → 回歸測試先紅 → 最小修正;根因是 SPEC 錯則升級 T2。

### B6 🟡 沒有分支、審查與收尾規範

- 目前工作區在 `feat/m4-2-episodic-memory-m4-6-topic-anchors` 上堆了 22 個已修改檔與 20+ 個未追蹤項目,橫跨 M3、M4、M6、docs、品牌素材,與分支名稱無關。
- 根目錄有除錯殘留:`corruptions.txt`、`debug_report.txt`、`temp_prev_session/`、`Claude outputs/`。
- 沒有審查步驟;沒有規定誰決定 push / PR。

**處置**:DEV_WORKFLOW §7 (一個 change 一個分支、開工前 `git status` 乾淨)、P6 審查清單、P7 收尾讓使用者選擇;DoD 包含「無除錯殘留」。

### B7 🟡 多個文件自稱「唯一權威」

`06_implementation_phases.md` 自稱「下一步做什麼的唯一權威」,但實際的下一步 (D-3:M4.7a → M0.5 → M5) 寫在 `MVP_CLOSURE_REPORT.md` §7 與 AI 記憶中;另有 7 份 Phase Closure Report、`REFINEMENT/`、`LEGACY/` 沒有標示是否仍有效,AI 可能讀到過時計畫。
**處置**:DEV_WORKFLOW §2「真相來源表」逐項指定唯一權威;`00_README.md` 標明歷史文件。**未修**:把 MVP_CLOSURE_REPORT §7 的決策回寫進 `06` (§E)。

---

## C. 冗贅與錯位的摩擦 (浪費注意力與 token)

### C1 🟢 同一套「閱讀順序」寫了三份,且彼此不一致

| 位置 | 順序 |
| ---- | ---- |
| 舊 `CLAUDE.md` 鐵則 1 | registry → research → risk → SPEC |
| 舊 `implement-module` | SPEC → research → audit |
| 舊 `00_README.md` | CLAUDE.md → registry → research → risk → SPEC |

而且鐵則 1 要求 `view` 整份 `03` (1004 行) 與 `05` (1373 行),每個任務約 2400 行進 context。`view` 也不是 Claude Code 的工具名稱。
**處置**:只在 DEV_WORKFLOW §2 定義一次「定向 grep」讀法,其他文件引用它。

### C2 🟢 確認點放錯位置且重複

`audit-integration` 每次都要求「是否確認此計畫?(y/n)」,`implement-module` 又在 Step 3 呼叫它——一個任務可能被問多次,而真正需要使用者判斷的「要不要改這個行為」反而沒有固定關卡。
**處置**:所有確認併入單一 G1 (提案拍板);稽核結果寫進 proposal,不另外問。

### C3 🟡 指示 AI「拒絕」使用者

舊 `implement-module`:「順便也做 M4.X 吧 → 拒絕」「測試太嚴格了,放寬一點 → 拒絕,SPEC 是合約」。使用者是 SPEC 的擁有者,拒絕只會造成爭論;正確做法是**導流**。
**處置**:改為「記入 proposal 後續,或更新 proposal / delta 後再做」;放寬斷言 = 改需求 = 回 P2。

### C4 🟢 引用要求過度

舊 `implement-module`:「每個 non-trivial function 都要引用研究」,commit 範本對基礎設施也要研究段落,與 `cite-research`「純 CRUD / UI 不要用本 skill」互相矛盾,誘發硬湊引用。
**處置**:統一為「只有研究推導的決策才引用」(憲章第六條)。

### C5 🟢 SPEC 驗收標準寫成 Python 偽碼

範本 §6 用 `def test_xxx(): ...` 描述驗收,把規格綁在實作上,也無法穩定引用某一條需求。
**處置**:改為 OpenSpec 式 `REQ-Mx.y-NN` + SHALL + GIVEN/WHEN/THEN,一個情境 = 一個測試,delta 可以用編號精準 ADDED / MODIFIED / REMOVED。

### C6 🟢 舊憲章的格式瑕疵

除錯段編號 1,2,3,4,6,7,8 (缺 5);「整合稽核」被引用為「CLAUDE.md §5」但鐵則 5 才是它,章節編號脆弱。
**處置**:改以「第一條~第七條」命名的憲章條款。

---

## D. 保留的優點

以下內容品質好,已原意保留進新憲章:

- 隱私三層 (L1/L2/L3) 與上雲必經 M2.2.2 + M2.3
- 心理機制不變式:草稿與核准、XP 守門、微摩擦、斷點推播、Persona 反向安撫
- `[Rxx: 關鍵字 §章節]` 引用格式與禁止模糊引用
- 整合風險 RISK-xx 四段式 (觸發組合 → 失效機制 → 緩解 → 驗收測試)
- 模組編號前綴命名、必須詢問使用者的清單、技術棧、Windows 除錯備忘

---

## E. 本次未處理 (建議後續各開一個 change)

| 項目 | 原因 |
| ---- | ---- |
| 修正根目錄 `pnpm test` 的後端路徑;CI 擴大到全部可離線執行的測試目錄 | 屬基礎設施變更,需驗證 CI 環境 (哪些測試依賴 `.env`、真實 DB) |
| 把 `MVP_CLOSURE_REPORT.md` §7 的路線決策 (D-3) 回寫到 `06_implementation_phases.md` | 涉及路線圖,應由使用者確認 |
| 清理 `services/main.py` 的靜默 `except … pass` | 每處需判斷是否為刻意降級,屬 T1/T2 |
| 根目錄除錯殘留 (`corruptions.txt`、`debug_report.txt`、`temp_prev_session/`、`Claude outputs/`) 的去留 | 刪除需使用者確認 |
| `SPEC_DEVIATION_REPORT.md` 未拍板條目 (如 DEVIATION-01) 逐條轉成 change | 每條都需要使用者拍板 |
| 既有 SPEC 的 `版本 / 狀態` 欄位校正 | 需逐份判斷是否已定案;依 DEV_WORKFLOW §10 漸進處理 |

---

## F. 本次變更清單

| 檔案 | 動作 |
| ---- | ---- |
| `CLAUDE.md` | 重寫:任務分級路由 + 七條憲章 + 專案地圖 + 已驗證指令;領域規則原意保留 |
| `docs/DEV_WORKFLOW.md` | 新增:流程唯一權威 (T0~T3、P1~P7、G1~G4、DoD、commit、反模式、框架對照) |
| `docs/DEV_PROCESS_AUDIT.md` | 新增:本報告 |
| `docs/changes/README.md`、`_templates/{proposal,design,tasks}.md`、`_templates/specs/SPEC_NAME.delta.md`、`archive/` | 新增 |
| `docs/modules/_TEMPLATE_SPEC.md` | 改:狀態 / 版本拆分、REQ + 情境格式、§9 規則、變更紀錄 |
| `docs/00_README.md` | 重寫:正確的文件樹、grep 現查數量、新標記符號 |
| `.claude/skills/propose-change/SKILL.md` | 新增 (P1~P3) |
| `.claude/skills/archive-change/SKILL.md` | 新增 (P7) |
| `.claude/skills/implement-module/SKILL.md` | 重寫為 P4~P6,修正路徑、移除「拒絕使用者」 |
| `.claude/skills/audit-integration/SKILL.md` | 稽核結果併入提案 (不另問 y/n)、grep 為準、補 M0.5 |
| `.claude/skills/cite-research/SKILL.md` | 移除寫死的編號上限、改定向讀取 |
