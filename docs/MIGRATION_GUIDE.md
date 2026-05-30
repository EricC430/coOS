# 從目前資料遷移到 VS Code Claude Code 的完整流程

> 你問:「我要了解在 VS Code 的 Claude Code 如何根據這些文件進行開發,是否要特殊指令、檔案結構、開發對話流程、SPEC 設計、對話附件、MCP Server 安裝等等,需如何將目前的資訊備妥遷移到 VS Code」
>
> 這個文件直接回答以上所有問題。

## 一、你目前手上有什麼,本套件做了什麼

### 你提供的原始材料

| 檔案 | 性質 | 在新流程中的位置 |
| ---- | ---- | ---------------- |
| `產品架構與技術需求綜合分析報告v2.md` | 產品願景 | 已蒸餾為 `docs/01_product_vision.md` |
| `系統架構與技術選型總覽.md` | 技術骨架 | 已併入 `docs/02_architecture.md` |
| `儲存架構與資料庫設計文件.md` | DB schema | 將寫入 `docs/modules/M6_*_SPEC.md` |
| `軟體介面構想.pdf` | UI Wireframe | 對應到 M3.x 系列 SPEC |
| `Life_OS_極致顆粒度開發樹狀藍圖.md` | 模組樹 | 已重構為 v4 (上一輪),再細化為 SPEC |
| 10 篇深度研究報告 | 學術依據 | **已建立 R01~R10 索引**,見 `docs/03_research_index.md` |

### 本套件新增的關鍵文件 (這就是「遷移到 VS Code 需要的所有東西」)

```
coOS/
├── CLAUDE.md                         ← 鐵則,Claude Code 每次必讀
├── README.md                         ← 給人類的入口
├── .claude/skills/                   ← 三個自動觸發的 skill
│   ├── cite-research/SKILL.md        ← 強制學術引用格式
│   ├── audit-integration/SKILL.md    ← 強制整合風險稽核
│   └── implement-module/SKILL.md     ← 強制七步實作協議
├── .mcp.json                         ← MCP server 配置
└── docs/
    ├── 00_README.md                  ← 文件地圖
    ├── 01_product_vision.md          ← 產品定位
    ├── 02_architecture.md            ← 技術架構
    ├── 03_research_index.md          ← ★ 10 篇研究的標準引用索引
    ├── 04_module_research_matrix.md  ← ★ 模組 ↔ 研究映射矩陣
    ├── 05_integration_risk_audit.md  ← ★ 12 條整合風險稽核 (回答你問的「合併效果變差」)
    ├── 06_implementation_phases.md   ← MVP 建構順序
    ├── SETUP_VSCODE.md               ← VS Code 設置完整步驟
    └── modules/
        ├── _TEMPLATE_SPEC.md         ← SPEC 模板
        └── M4_2_persona_state_machine_SPEC.md  ← 完整範例 SPEC
```

## 二、回答你的六個具體問題

### Q1:是否需要特殊指令?

**部分需要**。

| 場景 | 你需要打的指令 |
| ---- | -------------- |
| 開啟 Claude Code | VS Code: `Cmd/Ctrl+Shift+P` → `Claude Code: Open Chat`<br>Terminal: `claude` |
| 切換 permission mode | 在 Claude Code panel: `/mode` 然後選 `edit` / `auto-accept` / `plan` |
| 開新對話分支 | `/branch` (原 `/fork`,v2.1.77 改名) |
| 簡短側問,不污染主對話 | `/ask` 或 `/branch` |
| 查 MCP 狀態 | `/mcp` |
| 查 context 用量 | `/context` |
| 接續上次對話 | `/resume` |

skills 不需手動觸發,Claude Code 會根據你的任務描述自動選擇。你也可以強制觸發:

```
請使用 implement-module skill 來實作 M4.2
```

### Q2:檔案結構是什麼?

如上方目錄樹。**最關鍵的三點**:

1. `CLAUDE.md` 必須在**專案根目錄**。VS Code 必須開啟根目錄,不能只開子資料夾。
2. `.claude/skills/<skill_name>/SKILL.md` 是 skill 的標準結構,每個 skill 必須有 SKILL.md。
3. `docs/modules/Mx_y_*_SPEC.md` 是模組 SPEC 的命名規則,Claude Code 會根據此模式 grep。

### Q3:開發對話流程?

針對「實作模組」這種主任務,標準流程:

```
[你] 我要實作 M4.5 XP 自動結算

[Claude Code 自動觸發 implement-module skill]
[Step 1] view docs/modules/M4_5_*_SPEC.md
[Step 2] view docs/03_research_index.md 找 R08
[Step 3] invoke audit-integration → 發現 RISK-01
[Step 4] 提出 Audit Summary,問你是否確認計畫
       ↓
[你] 確認

[Claude Code Step 5] 寫測試
[Claude Code Step 6] 寫程式碼
[Claude Code Step 7] 跑測試,迭代直到全綠
       ↓
[Claude Code] 產出 commit message 草稿,等你 review

[你] commit message 改一下,加上 ...

[Claude Code] git commit
```

針對「腦力激盪」或「審查」這種副任務,用 plan mode 或 subagent。

### Q4:SPEC 如何設計?

**已經設計好標準了**,見 `docs/modules/_TEMPLATE_SPEC.md`。

每個 SPEC 必須有 9 個區塊:

1. Purpose
2. References (對應 R01~R10)
3. Inputs / Outputs
4. Dependencies
5. Known Risks (對應 RISK-01~12)
6. Acceptance Criteria (測試清單)
7. Implementation Notes
8. Anti-patterns
9. Open Questions

完整範例見 `M4_2_persona_state_machine_SPEC.md`(這是真的可以照抄的工作範例)。

**SPEC 寫作流程**:

```
1. 開新檔案 docs/modules/Mx_y_NAME_SPEC.md
2. 把 _TEMPLATE_SPEC.md 的內容貼過來
3. 一格一格填
4. §2 References:強制至少 1 個 Rxx (若無 → 此模組可能不該存在,或屬基礎設施)
5. §5 Known Risks:grep docs/05_integration_risk_audit.md 看哪些 RISK 觸發
6. §6 Acceptance Criteria:**先寫測試,後寫實作**
7. §9 Open Questions:至少 1 個 (沒有 → 思考不足)
```

也可以**讓 Claude Code 幫你寫 SPEC**:

```
[在 Claude Code panel]

請依 docs/modules/_TEMPLATE_SPEC.md 模板,為 M3.3.3 草稿核准彈窗寫一份 SPEC。

引用:
- R08 微摩擦力章節
- R10 MindScape 章節

整合風險:
- RISK-01 (XP 提前發放)

完成後等我 review,不要產生 React 程式碼。
```

### Q5:對話附件?

Claude Code 可以接收檔案附件,但有更好的做法:

**方式 A:用 @-mention** (推薦)

```
@docs/03_research_index.md 請依 R03 §3.2 設計 Echo Mode 的測試案例
```

Claude Code 會自動讀取 @ 指定的檔案。

**方式 B:用相對路徑提示**

```
請讀 docs/modules/M4_2_persona_state_machine_SPEC.md 後告訴我 §6 Acceptance Criteria
```

**方式 C:複雜貼附** (例如要分析一段你寫的程式碼)

```
分析以下程式碼是否違反 CLAUDE.md §隱私三層原則:

[paste code here]
```

**不建議的方式**:

- ❌ 拖拉 PDF 進對話 (Claude Code 對 PDF 支援不如 markdown)
- ❌ 一次貼超過 5000 行 (會吃光 context)

### Q6:MCP Server 安裝?

`.mcp.json` 已經建好。**MVP 階段建議啟用兩個**:

1. `filesystem` — 預設啟用,Claude Code 預設就能讀寫,但 MCP 提供精細權限
2. `sqlite-local` — 讓 Claude Code 可以直接查 `raw_tracking_logs` 除錯

```bash
# 安裝
npm install -g @modelcontextprotocol/server-filesystem
uvx install mcp-server-sqlite  # 或 pip install mcp-server-sqlite
```

**進階階段才啟用**:

3. `github` — 讓 Claude Code 操作 PR/Issue
4. `postgres` — 讓 Claude Code 查雲端 DB (僅讀取)
5. `neo4j` — 讓 Claude Code 視覺化薩提爾圖譜

**警告**:每個 MCP server 啟動時會把工具定義載入 context,**最多 3 個同時開**,否則 context 一開始就被吃掉一半。用 `/mcp` 可以暫時停用某個。

## 三、現在開始的精確流程 (60 分鐘上線)

### 步驟 1: 取得套件 (5 分鐘)

**macOS / Linux:**
```bash
mkdir coOS && cd coOS
# 把這個 ZIP 解壓進來
unzip ~/Downloads/coos_package.zip
ls
# 確認看到: CLAUDE.md, README.md, docs/, .claude/, .mcp.json
```

**Windows (PowerShell):**
```powershell
mkdir coOS
cd coOS
# 把這個 ZIP 解壓進來 (請根據您實際的 ZIP 檔案路徑與名稱調整)
Expand-Archive -Path "$env:USERPROFILE\Downloads\coos_package.zip" -DestinationPath .
dir
# 確認看到: CLAUDE.md, README.md, docs/, .claude/, .mcp.json
```

### 步驟 2: 環境工具 (15 分鐘)

**macOS / Linux:**
```bash
# Node.js (LTS) + Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Python 3.11+ 與 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Rust (給 Tauri)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Windows (PowerShell):**
```powershell
# Node.js (LTS) + Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Python 3.11+ 與 uv
irm https://astral.sh/uv/install.ps1 | iex

# Rust (給 Tauri)
# 請至 https://rustup.rs/ 下載並執行 rustup-init.exe 進行安裝
```

### 步驟 3: VS Code Extension (5 分鐘)

```
1. Cmd/Ctrl+Shift+X 開 Extensions
2. 搜尋 "Claude Code"
3. 安裝 publisher: anthropic
4. 重啟 VS Code
5. 確認左側欄出現 Claude 圖示
```

### 步驟 4: 認證 (2 分鐘)

```bash
claude auth
# 開瀏覽器登入 (需要 Pro/Max 訂閱)
```

### 步驟 5: 開啟專案 (1 分鐘)

```bash
code .
# 重要:開啟整個 coOS/ 資料夾,不是單一檔案
```

### 步驟 6: 第一次對話測試 (10 分鐘)

```
[Cmd/Ctrl+Shift+P → Claude Code: Open Chat]

[第一條訊息]
請完成以下三項驗證,並以結構化清單回報:

1. 讀 CLAUDE.md,提取出「不要做的事」前三條
2. 從 docs/03_research_index.md 找出 R03 的全名與三個主要技術詞彙
3. 從 docs/05_integration_risk_audit.md 找出 RISK-03 的觸發組合與緩解策略一句話描述

不要產生任何程式碼。
```

如果它做不到上述任一項,**先別開工**,排除設置問題。

### 步驟 7: 啟動 Phase 0 (20 分鐘)

```
[第二條訊息]
進入 Plan Mode。請列出 docs/06_implementation_phases.md 中 Phase 0 的所有任務,並針對每項:
- 估計工時
- 列出觸發的 RISK (若有)
- 列出需要的工具

最後提議第一個動工的任務。
```

審 plan → 切回 Edit mode → 動工。

### 步驟 8: 寫第一段程式碼

```
[第三條訊息]
切回 Edit mode。開始實作第一個任務:M0.1 Monorepo 專案結構初始化。

依 implement-module skill 的七步協議進行。
M0.1 沒有對應的 SPEC (屬基礎設施),所以可以略過 Step 1-2,但 Step 4 (先寫測試) 仍要遵守。
```

到這裡你就跑完整流程一次。後續每個模組都重複此模式。

## 四、進度追蹤建議

### Daily

- 開工:`git pull` + `/resume` 或新對話 + read CLAUDE.md
- 收工:`pytest && pnpm test` + Claude Code 產 commit message + push

### Weekly

- 跑全測試報告:`pytest -v --tb=short > weekly_report.txt`
- Review 觸發的 RISK 是否已對應寫測試標記:`grep -r "integration_risk" tests/`
- 更新 `docs/MVP_CLOSURE_REPORT.md`(若達 Phase 結尾)

### 每完成 Phase

- 產出 Phase Closure Report
- 跑全模組整合風險稽核
- Sync `.claude/skills/` 中如果有新發現的反模式

## 五、本套件 vs 你原本資料的差異總結

| 維度 | 你原本有 | 本套件新增 |
| ---- | -------- | ---------- |
| 產品願景 | ✅ 詳盡的 v2 報告 | 蒸餾為 5 分鐘可讀的 `01_product_vision.md` |
| 技術骨架 | ✅ 系統架構文件 | 整合為清晰的 4 層架構 + 隱私三層分類 |
| 模組劃分 | ✅ v3.0 樹狀藍圖 | 已重構為 v4 (上一輪) + SPEC 模板 |
| 研究依據 | ✅ 10 篇研究 | **R01~R10 索引 + 引用標準格式 + 模組映射矩陣**(以前散落,現在可 grep) |
| 整合風險 | ❌ 無 | **12 條 RISK 稽核**(回答你問的「合併變差」) |
| 實作順序 | 模糊 | Phase 0~6 明確,有閉環標準 |
| Claude Code 配置 | ❌ 無 | **`CLAUDE.md` + 3 個 skills + `.mcp.json`** |
| 對話流程規範 | ❌ 無 | implement-module 七步協議 |

## 六、如果你想擴展

### 寫更多 SPEC

我只寫了 M4.2 一個完整 SPEC 作為範例 (因為它是最複雜的)。你可以:

```
[對 Claude Code 說]
依 docs/modules/_TEMPLATE_SPEC.md 模板,為 M3.3.3 寫 SPEC。
引用 R08 §四 與 §六,參考 RISK-01。
完成後給我看,不要寫實作。
```

它會產出可用的 SPEC,你 review 後存檔即可。

### 新增第 11 篇研究

```
1. 在 docs/03_research_index.md 末尾新增 R11
2. 用相同 schema (全名、技術詞彙、主要模組、章節索引、範例)
3. 更新 docs/04_module_research_matrix.md
4. 若觸發新風險,新增 RISK-13
```

### 新增第 13 條 RISK

```
1. 在 docs/05_integration_risk_audit.md 末尾新增 RISK-13
2. 依四欄填寫 (觸發/失效/緩解/驗收)
3. 更新對應模組 SPEC 的 §5 Known Risks
4. 寫 @pytest.mark.integration_risk("RISK-13") 測試
```

## 七、最後一句話

**這個套件的價值在於:讓 Claude Code 在沒有你 supervise 的情況下也不會做出違反隱私、學術依據、心理安全的事**。

你交給它一個模組編號,它能:
- 自己讀 SPEC
- 自己找研究引用
- 自己稽核整合風險
- 自己寫測試
- 自己迭代到全綠
- 自己產出可審查的 commit message

你的時間用在 review 它的 plan 與 commit,而不是 babysit 每行程式碼。

這就是「將目前的資訊備妥遷移到 VS Code」的完整答案。
