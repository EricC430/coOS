# coOS 開發流程 (Spec-Driven Development Workflow)

**狀態**:`approved`
**版本**:`1.0`
**最後更新**:2026-10-19
**取代**:CLAUDE.md 舊版「鐵則 1~5」中分散的流程描述、`implement-module` skill 舊版七步驟

> 本檔是「**怎麼做**」的唯一權威;`CLAUDE.md` 是「**什麼不能違反**」的唯一權威。
> 兩者衝突時以 `CLAUDE.md` 憲章條款為準,並回報衝突。
>
> 設計參照:GitHub **Spec Kit** (constitution → specify → clarify → plan → tasks → analyze → implement)、
> **OpenSpec** (現況規格與變更提案分離、delta spec、archive 合併)、
> **Superpowers** (brainstorming、writing-plans、TDD、systematic-debugging、verification-before-completion)。
> 對照表見 §9。為什麼要改,見 `docs/DEV_PROCESS_AUDIT.md`。

---

## 0. 一頁總覽

```
                     ┌───────────────────────────────────────────────┐
  使用者需求 ──▶ 分級 │ 「改完之後,SPEC 上的文字還對嗎?」              │
                     └───────┬───────────────┬───────────────┬───────┘
                             │對,只是小改    │對,但程式壞了  │不對 / 沒有 SPEC
                             ▼               ▼               ▼
                        T0 Quick        T1 Fix          T2 Change / T3 New Module
                        直接改+驗證     §5 除錯流程      §3 完整 SDD 流程
                                                          │
   ┌──────────────────────────────────────────────────────┘
   ▼
  P1 釐清 ─▶ P2 提案 ─▶ [G1 使用者拍板] ─▶ P3 計畫 ─▶ [G2 一致性檢查]
                                                          │
  P7 歸檔 ◀─ [G4 審查] ◀─ P6 審查 ◀─ [G3 證據] ◀─ P5 驗證 ◀─ P4 TDD 實作
   │
   └─▶ delta 合併進 SPEC、change 移入 archive、更新 04/05/06 與報告
```

只有 **G1 (提案拍板)** 一定要停下來等使用者;其他關卡由 Claude 自查並把證據寫進輸出。

---

## 1. 分級 (Track):先決定走哪條路

| Track | 判定條件 | 例子 | 流程 | 需要 change 資料夾? |
| ----- | -------- | ---- | ---- | -------------------- |
| **T0 Quick** | 不改任何 SPEC 所定義的行為、契約、資料結構 | 錯字、註解、文件連結、純樣式微調、ruff 修正 | 直接改 → §4 驗證 → commit | 否 |
| **T1 Fix** | SPEC 已定義正確行為,程式碼不符 | 500 錯誤、例外被吞、測試紅燈 | §5 除錯流程 | 否 (除非根因是 SPEC 錯 → 升級 T2) |
| **T2 Change** | 改變/新增/移除 SPEC 行為;新 API 欄位;schema 變更;跨模組新依賴;調整任何常數門檻 | 套問上限 1→3、新增 SSE 事件、加欄位 | §3 完整流程 | **是** |
| **T3 New Module** | 該 `Mx.y` 沒有 SPEC,或 SPEC 狀態為 `draft` | 實作 M4.7a、M5.1 | §3 完整流程 + 新 SPEC | **是** |

**判斷不出來 → 當 T2。** 走錯成 T2 只多花幾分鐘;走錯成 T0 會產生下一條 `DEVIATION-xx`。

升級規則:

- T0 過程中發現需要改行為 → 停,升級 T2。
- T1 根因分析後發現「SPEC 本身寫錯 / 寫漏」→ 停,升級 T2 (先改規格再修碼)。
- 任何 Track 碰到憲章條款 (隱私三層、R08 草稿與核准、XP 守門) → 一律 T2,且提案須明列該條款。

---

## 2. 真相來源 (Source of Truth)

| 問題 | 唯一權威 | 備註 |
| ---- | -------- | ---- |
| 不可違反的規則 | `CLAUDE.md` | 憲章 |
| 怎麼開發 | `docs/DEV_WORKFLOW.md` (本檔) | |
| 系統**現在**應該怎麼運作 | `docs/modules/Mx_y_*_SPEC.md` | 只描述已核准行為;不寫「未來想做」 |
| 系統**將要**怎麼改 | `docs/changes/<change-id>/` | 進行中的提案 |
| 改過什麼、為什麼 | `docs/changes/archive/` + git log | |
| 有哪些模組、標籤、依賴 | `docs/04_module_registry.md` | |
| 研究依據 | `docs/03_research_index.md` | |
| 整合風險 | `docs/05_integration_risk_audit.md` | |
| 下一步做什麼 (路線圖) | `docs/06_implementation_phases.md` | Closure Report 是歷史快照,不是路線圖 |
| 既有偏離 / 缺口待辦 | `docs/SPEC_DEVIATION_REPORT.md`、`docs/IMPLEMENTATION_GAP_REPORT.md` | 只登記「**事前沒走 change 流程**就已存在」的落差;每條以一個 change 關閉 |

**讀文件的方式:定向擷取,不整份讀。** `03` 有 1000+ 行、`05` 有 1300+ 行,整份讀入只會稀釋注意力:

```bash
grep -n -A 40 "^### M4.4 " docs/04_module_registry.md          # 模組條目
grep -n -A 35 "^## R08 " docs/03_research_index.md             # 單篇研究
grep -n "M4\.4\|M6\.5" docs/05_integration_risk_audit.md       # 找出相關 RISK 行號
grep -n "^## RISK-" docs/05_integration_risk_audit.md          # 風險總表 (永遠比任何快取表新)
```

---

## 3. T2 / T3 完整流程

### P1 釐清 (Clarify) — 對應 Superpowers brainstorming、Spec Kit `/clarify`

**進入**:分級為 T2/T3。
**動作**:

1. 定向讀取:SPEC (若有) → `04` 模組條目 → SPEC §2 引用的 `03` 章節 → `05` 相關 RISK。
2. 用自己的話把需求重述成一句「使用者 / 系統在 X 情境下應該 Y,因為 Z」。
3. 找出模糊點,**一次問一個問題**;能從程式碼或文件查到的不要問。
4. 有設計選擇時,提出 2~3 個方案 + 取捨 + 你的建議 (不要只給一個,也不要列一大堆)。
5. 碰到研究約束 (例:R08 摩擦、R03 反向安撫) 時,明確指出「此需求會鬆綁 [Rxx §y]」,鬆綁只能由使用者拍板。

**產出**:釐清後的需求,足以寫 `proposal.md`。
**不准**:在本階段寫任何程式碼或測試。

### P2 提案 (Propose) — 對應 OpenSpec `proposal` + delta spec、Spec Kit `/specify`

**動作**:

1. 取 change-id:動詞開頭 kebab-case,帶模組號,例 `m4-4-per-context-probe-limit`、`add-m4-7a-vault-reader`。
2. 建立 `docs/changes/<change-id>/`,從 `docs/changes/_templates/` 複製:
   - `proposal.md` (必要) — Why / What Changes / Impact / Out of Scope / 拍板項
   - `specs/<SPEC 檔名>.delta.md` (必要,每個受影響 SPEC 一份) — `ADDED / MODIFIED / REMOVED Requirements`,每條需求至少一個 `WHEN/THEN` 情境
   - `design.md` (條件必要) — 跨 2+ 模組、schema 變更、新外部依賴、研究推導的演算法、或有 2 個以上可行方案時才寫
3. T3 新模組:在 `docs/modules/` 依 `_TEMPLATE_SPEC.md` 建立 SPEC,`狀態: draft`;它本身就是 delta (全部屬 ADDED)。
4. 呼叫 skill **`audit-integration`**,把稽核結果寫進 `proposal.md` 的「整合風險」段 (**不另外問 y/n**,併入 G1)。
5. 所有「待使用者拍板」問題以 `[NEEDS DECISION]` 標記列在 `proposal.md` 末尾,**最多 5 個**,每個附建議答案。

**閘門 G1 — 提案拍板 (必停)**:把 `proposal.md` 摘要 + delta 重點 + 風險 + `[NEEDS DECISION]` 呈給使用者,等明確同意。
同意後在 `proposal.md` 填 `狀態: approved` 與日期,`[NEEDS DECISION]` 改寫成「拍板:…」。

### P3 計畫 (Plan & Tasks) — 對應 Superpowers writing-plans、Spec Kit `/plan` `/tasks` `/analyze`

**動作**:

1. 寫 `tasks.md`:有序、可勾選,每個任務是「**一個測試 + 讓它通過的最小實作**」的單位 (約 2~15 分鐘),寫出:
   - 要改 / 新增的**確切檔案路徑** (遵守 CLAUDE.md §專案地圖)
   - 對應的需求編號 `REQ-Mx.y-NN` 與情境
   - 要跑的**確切指令**與預期結果 (紅燈時預期哪個錯誤)
2. 依賴順序:資料層 (M6) → 邏輯 (M4/M5) → API (`services/main.py` 掛載) → 前端 (M3) → 閉環測試 → 文件。
3. **一致性分析 (Analyze)**,在 `tasks.md` 末尾填表:
   - 每條 ADDED/MODIFIED 需求的每個情境 → 至少 1 個任務 → 至少 1 個測試名稱
   - 每個觸發的 RISK → 至少 1 個 `@pytest.mark.integration_risk("RISK-xx")` 測試
   - 每個 REMOVED 需求 → 有刪除對應程式碼 / 測試的任務
   - 跨 2+ 模組 → 至少 1 個閉環 (closed-loop) 測試任務 (參考 `testing/m4_5/test_mvp_closed_loop.py`)

**閘門 G2 — 一致性**:上表沒有空格。有空格就補任務或回 P2 改 delta。T3 或任務數 > 15 時,把 `tasks.md` 給使用者過目 (不需拍板,可直接繼續)。

### P4 實作 (TDD) — 對應 Superpowers test-driven-development、Spec Kit `/implement`

每個任務嚴格執行:

1. **Red**:寫測試 → 執行 → **親眼確認**它因為「功能不存在 / 行為不對」而失敗 (不是 import 錯誤、不是路徑錯誤、不是沒被收集到)。
2. **Green**:寫讓它通過的最小實作。
3. **Refactor**:整理,測試保持綠燈。
4. 勾選 `tasks.md`,commit (見 §7)。一個任務或一組緊密任務一個 commit。

實作中的規則:

- **規格先於程式碼**:實作時發現 delta 寫錯 / 寫漏 → 先改 delta (必要時回 G1),再改程式碼。永遠不留「程式碼和 SPEC 不一致、之後再補登」的狀態。
- **範圍外的需求** (使用者臨時加的、自己發現的) → 記到 `proposal.md` 的「後續」段,或另開 change;不要順手做。若使用者堅持併入本 change,先更新 proposal/delta 再做。
- **不准吞例外**:禁止 `except: pass` / `except Exception: return None` 而不寫 log。跨模組互動寫入 `raw_tracking_logs` (M0.4)。
- **同一測試修 3 次仍失敗 → 停**,轉 §5 除錯流程找根因,或回報「SPEC 不夠精準」。
- 不要為了讓測試通過而改鬆測試的斷言;要改斷言 = 改需求 = 回 P2。

### P5 驗證 (Verify) — 對應 Superpowers verification-before-completion

**原則:沒有新鮮的執行證據,就不能說「完成」「通過」「修好了」。**

必跑 (依改動範圍):

```bash
# 後端全套 (~5 分鐘,排除需要 sidecar / iPad 的測試)
cd services && .venv/Scripts/python.exe -m pytest ../testing/ --ignore=../testing/local_llm --ignore=../testing/m0_2 -q 2>&1 | tail -15
# 前端
pnpm --filter @coos/desktop test 2>&1 | tail -15
# Lint
cd services && uv run ruff check . && cd .. && pnpm --filter @coos/desktop lint
```

另外:

- **跨模組 change**:閉環測試必須通過 (單元測試全綠但接縫斷掉,是本專案已經發生過的失效模式,見 `MVP_CLOSURE_REPORT.md` §9.2)。
- **使用者可見的改動** (API、UI):實際打一次 endpoint 或用 `.claude/launch.json` 的 `coos-desktop` 開起來看,並檢查 `raw_tracking_logs` 有對應事件。
- **Schema 變更**:migration 只產生檔案,呈給使用者審;不可自行 apply 到真實 `data/coos.db`。

**閘門 G3 — 證據**:回報時附上「指令 + 通過/失敗/跳過數」。測試數比 change 開始前少 → 必須解釋。

### P6 審查 (Review) — 對應 Superpowers requesting-code-review

1. 對照 delta 逐條自審:每個情境都有對應程式碼與測試?有沒有實作了 delta 沒寫的行為?
2. 憲章檢查清單:
   - [ ] 沒有 L1 明文 (程式碼、對話逐字稿、瀏覽內容) 進入任何雲端 LLM 呼叫路徑
   - [ ] 沒有自動寫 `is_reviewed = true`;XP 只在守門員條件全滿足時發放
   - [ ] 沒有移除微摩擦 (必填欄位、核准步驟)
   - [ ] Persona 對使用者負面情緒是反向安撫,不是鏡像
   - [ ] `[MVP]` 程式碼沒有硬依賴 `[進階]` 模組
   - [ ] 研究推導的決策都有 `[Rxx: 關鍵字 §章節]`
3. 改動 > 300 行或跨 3+ 模組:使用 `/code-review` (或 Superpowers requesting-code-review) 做獨立審查,處理所有正確性問題。

**閘門 G4**:清單全勾,審查發現已處理或明列為後續。

### P7 歸檔 (Archive) — 對應 OpenSpec `archive`

呼叫 skill **`archive-change`**:

1. 把每份 `specs/*.delta.md` 合併進 `docs/modules/` 對應 SPEC (ADDED 加入、MODIFIED 取代整條需求、REMOVED 刪除並在 SPEC 變更紀錄留一行)。
2. SPEC 標頭:版本號遞增 (行為變更 → minor;只補文字 → patch)、`最後更新`、`狀態` (`draft → approved → implemented`)。
3. 依影響更新:`04` (標籤、依賴、Criteria)、`05` (新 RISK 或緩解狀態)、`06` (路線圖勾選)。
4. 本 change 若關閉了 `DEVIATION-xx` / `GAP-xx`,在對應報告標 ✅ 並寫上 change-id。
5. 把資料夾移到 `docs/changes/archive/YYYY-MM-DD-<change-id>/`,更新 `docs/changes/README.md` 索引。
6. 收尾分支:列出選項 (commit 到本分支 / 開 PR / 保留) 讓使用者決定;**不自行 push 或開 PR**,除非使用者要求。

---

## 4. T0 Quick 流程

1. 確認真的不改行為 (§1 判定)。
2. 改。
3. 跑受影響範圍的測試或 lint (文件改動:確認連結 / 路徑存在)。
4. commit:`docs: …` / `chore: …` / `style(m3.2): …`。

---

## 5. T1 Fix 流程 (系統化除錯) — 對應 Superpowers systematic-debugging

**原則:沒找到根因前不准修。** 連續 commit「repairment」「patching」是在猜,不是在修。

1. **重現**:寫出最小重現步驟或指令,記錄實際輸出 vs SPEC 預期 (引用 `REQ-` 或 SPEC 章節)。
2. **蒐證**:先查 `raw_tracking_logs`、sidecar log、被吞的例外 (grep `except` 附近);不要猜。
3. **假設**:一次一個根因假設,用最小實驗驗證或否定。3 個假設都被否定 → 停下來回報,質疑架構或 SPEC。
4. **回歸測試 (Red)**:寫一個因此 bug 而失敗的測試,親眼看它失敗。
5. **修 (Green)**:最小修正,只修根因。
6. **驗證**:§3 P5 全套。
7. **commit**:`fix(mx.y): <症狀>` ,body 寫「根因:…」與測試名稱。
8. 若根因是 SPEC 錯或漏 → 升級 T2,不要用 fix 偷改行為。
9. 若修的是報告裡登記的 `GAP-xx` / `DEVIATION-xx`,同步標 ✅。

---

## 6. 完成定義 (Definition of Done)

一個 change 只有在以下全部為真時才算完成:

- [ ] `proposal.md` 狀態 `approved`,所有 `[NEEDS DECISION]` 已拍板
- [ ] `tasks.md` 全部勾選,一致性分析表無空格
- [ ] 每個需求情境都有通過的測試,且曾經親眼看過它紅燈
- [ ] 後端全套、前端、lint 通過,數字寫在回報裡;測試數未無故減少
- [ ] 跨模組 change 有通過的閉環測試
- [ ] P6 憲章清單全勾
- [ ] delta 已合併進 SPEC,change 已歸檔,`04/05/06` 與報告已同步
- [ ] 沒有留在工作區的除錯檔、暫存檔 (`debug_*.txt`、`temp_*`)

---

## 7. 分支與 Commit 規範

**分支**:一個 change 一個分支,從 `master` 切出。

| 類型 | 命名 |
| ---- | ---- |
| T2/T3 | `feat/<change-id>` |
| T1 | `fix/mx-y-<slug>` |
| T0 文件 | `docs/<slug>` |

不要把不相關的未提交改動堆在同一分支;開始新 change 前先確認 `git status` 乾淨,或請使用者決定如何處理既有改動。需要平行做多件事時用 git worktree (Superpowers using-git-worktrees)。

**Commit**:Conventional Commits,scope 用模組號。

```
feat(m4.4): limit elicitation to one probe per context type

Change: m4-4-per-context-probe-limit
Requirements: REQ-M4.4-03 (MODIFIED), REQ-M4.4-07 (ADDED)
依據: [Rxx: 關鍵字 §章節]   ← 從 03_research_index.md 查到的真實章節;查不到就不寫
風險: RISK-xx 緩解維持
測試: testing/m4_4/test_elicitation_cooldown.py (5 passed)

Co-Authored-By: ...
```

- 研究引用**只在**決策確實來自研究時寫;基礎設施、重構、UI 不必硬塞。
- 一個 commit 只做一件事;不要用 `update`、`patching`、`repairment` 當標題。

---

## 8. 反模式 (這些都在本專案發生過)

| 反模式 | 後果 | 正確做法 |
| ------ | ---- | -------- |
| 先改程式碼,之後在 `SPEC_DEVIATION_REPORT` 補登 | DEVIATION-01:套問上限被放寬、測試失敗、R08 緩解失效 | P2 先寫 delta,G1 拍板後再改 |
| 只看單元測試綠燈就宣告完成 | `/api/m4_5/grant_xp` 長期 500、XP 靜默寫入失敗 | P5 閉環測試 + 實際打 endpoint |
| `except: pass` 吞例外 | 「從來沒發生過」的事件其實一直失敗 | 寫 log;跨模組寫 `raw_tracking_logs` |
| 照 skill 裡寫死的路徑建測試 | 測試放在 pytest 不收集的目錄,假綠燈 | 以 CLAUDE.md §專案地圖為準,Red 階段確認測試真的被執行 |
| 寫死的速查表 (RISK、R 編號上限) | 新增 RISK-24/25 後速查表漏列 | 每次用 grep 現查 |
| 每個步驟都問使用者 y/n | 使用者疲勞、拍板品質下降 | 只在 G1 一次問清楚 |
| 「拒絕」使用者的範圍變更 | 爭論而非推進 | 導入 change 流程:改 proposal/delta 或另開 change |
| 整份讀 `03`/`05` | 浪費 context,重點被稀釋 | §2 定向 grep |
| 連續猜測式 fix commit | 三個「repairment」commit 才修好 | §5 先找根因 |

---

## 9. 與參考框架的對照

| coOS 階段 | Spec Kit | OpenSpec | Superpowers |
| --------- | -------- | -------- | ----------- |
| 憲章 `CLAUDE.md` | `constitution.md` | `project.md` | — |
| P1 釐清 | `/specify` + `/clarify` | — | brainstorming |
| P2 提案 + delta | `spec.md` | `changes/<id>/proposal.md` + `specs/` delta | — |
| P3 計畫 + 一致性 | `/plan` + `/tasks` + `/analyze` | `tasks.md` + `validate` | writing-plans |
| P4 TDD | `/implement` | `apply` | test-driven-development、subagent-driven-development |
| P5 驗證 | checklist | — | verification-before-completion |
| P6 審查 | — | — | requesting-code-review |
| P7 歸檔 | — | `archive` | finishing-a-development-branch |
| T1 除錯 | — | — | systematic-debugging |

刻意**不**照搬的部分:

- 不建立 `.specify/` 或 `openspec/` 目錄:沿用既有 `docs/modules/` 作為現況規格,避免兩套 SPEC。
- 不要求每個任務都派 subagent:本專案多數 change 規模小,inline 執行即可;任務 > 10 且彼此獨立時才考慮。
- 不為 T0/T1 開 change 資料夾:流程重量要和風險成比例。

---

## 10. 既有文件的遷移策略 (漸進,不一次重寫)

- 既有 45 份 SPEC **不批次改寫**。某份 SPEC 第一次被 change 觸及時,在該 change 的 delta 中把相關驗收標準改寫為 `REQ-` + `WHEN/THEN` 格式;未觸及的部分維持原樣。
- `SPEC_DEVIATION_REPORT.md` 中未拍板的 DEVIATION,每條以一個 T2 change 處理 (拍板結果寫進 delta)。
- `IMPLEMENTATION_GAP_REPORT.md` 的 GAP:行為已在 SPEC → T1;需要新行為 → T2。
- Phase Closure Report 保留為歷史;下一步一律以 `06_implementation_phases.md` 為準。
