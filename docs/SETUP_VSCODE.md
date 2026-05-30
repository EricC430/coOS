# VS Code + Claude Code 完整設置指南

> 此文件是「我已經有這個 docs/ 包,現在要在 VS Code 開始用 Claude Code」的完整步驟。

## 1. 先確認你需要什麼

| 你需要 | 用途 |
| ------ | ---- |
| Node.js 18+ | 跑 Claude Code CLI |
| VS Code 1.98+ | 跑 Claude Code Extension |
| Claude Pro/Max 訂閱 ($20/月起) | Free 版不能用 Claude Code |
| Git | 版本控制 |
| Python 3.11+ | 後端 |
| Rust 1.75+ | Tauri 殼 (透過 rustup) |
| pnpm | 前端套件管理 |

## 2. 安裝 Claude Code (5 分鐘)

```bash
# 安裝 CLI
npm install -g @anthropic-ai/claude-code
claude --version  # 應顯示 1.x.x

# 第一次認證 (會開瀏覽器)
claude auth
```

VS Code 端:

```
1. Cmd/Ctrl+Shift+X 開啟 Extensions
2. 搜尋 "Claude Code"
3. 安裝 publisher 為 anthropic 的那個 (2M+ 下載)
4. Cmd/Ctrl+Shift+P → "Claude Code: Open Chat"
```

VS Code 設定建議:

```json
// .vscode/settings.json
{
  "claudeCode.permissionMode": "edit",
  "claudeCode.autoSaveBeforeChanges": true,
  "claudeCode.showInlineDiffs": true
}
```

## 3. 把 docs/ 包遷移進 VS Code 專案 (10 分鐘)

```bash
# 建立你的專案
mkdir coOS && cd coOS
git init

# 把 docs/ 包複製進來 (假設你把 ZIP 解壓在 ~/Downloads/coos-docs)
cp -r ~/Downloads/coos-docs/. .

# 確認結構
ls -la
# 應該看到 CLAUDE.md, README.md, docs/, .claude/, .mcp.json
```

VS Code 開啟整個資料夾:

```bash
code .
```

**極重要**:**開啟整個資料夾,不是單一檔案**。Claude Code 需要看到 `CLAUDE.md` 與 `.claude/skills/` 才能正常運作。

## 4. 設定環境變數 (5 分鐘)

```bash
# 複製範本 (你需要先建立這個範本)
cat > .env.example <<'EOF'
# Cloud LLM
GEMINI_API_KEY=

# Edge Inference (iPad M1)
IPAD_AI_LOCAL_HOST=192.168.0.42:11434

# Cloud DB
SUPABASE_URL=
SUPABASE_KEY=
NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=

# OAuth (進階)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# 生圖 (MVP 階段)
# Pollinations.ai 無需 key
EOF

cp .env.example .env
# 編輯 .env 填入實際值
```

**安全注意**:

```bash
# 確保 .env 被 ignore
cat > .gitignore <<'EOF'
.env
.env.local
node_modules/
__pycache__/
*.pyc
target/        # Rust
dist/
build/
.DS_Store
data/*.db      # SQLite
EOF
```

## 5. 設定 MCP servers (10 分鐘)

`.mcp.json` 已經建好,只需修改路徑:

```bash
# 編輯 .mcp.json,把 /path/to/coos-project 改為實際路徑
# macOS/Linux:
sed -i '' "s|/path/to/coos-project|$(pwd)|g" .mcp.json
# Linux:
sed -i "s|/path/to/coos-project|$(pwd)|g" .mcp.json
```

驗證 MCP server 跑得起來:

```bash
# 在 VS Code Claude Code 對話框輸入:
/mcp
# 應顯示已連接的 MCP servers 清單
```

## 6. 第一次對話 (測試一切就緒)

在 VS Code Claude Code panel 輸入這條訊息:

```
請依照以下步驟驗證專案設置:

1. 讀 CLAUDE.md
2. 讀 docs/00_README.md
3. 列出 docs/modules/ 目錄下的所有 SPEC 檔案
4. 從 docs/06_implementation_phases.md 告訴我 Phase 0 該做什麼
5. 確認可以存取 .claude/skills/ 下的三個 skill

請以結構化清單回覆,不要產生程式碼。
```

Claude Code 的正確回應應該包含:

- 確認讀到 `CLAUDE.md` 的鐵則 (隱私三層、研究引用格式等)
- 列出文件包的 7 個主要 docs 檔案
- 找到 `M4_2_persona_state_machine_SPEC.md` 作為唯一存在的 SPEC
- 報告 Phase 0 的 6 個任務
- 確認三個 skills 都可讀

如果它做不到上述任一項,**先排除環境問題再開工**。

## 7. 啟動 Phase 0 — 跑一條真實任務

```
[在 Claude Code panel 輸入]

我要開始 Phase 0。請依以下步驟:

1. 進入 Plan Mode (我會審你)
2. 列出 Phase 0 的所有任務
3. 對每個任務:
   - 引用對應的研究 (如果有)
   - 標註涉及的模組
   - 警告觸發的整合風險
4. 提議第一個動工的任務

不要產出程式碼。
```

審核 plan → 確認 → 切回 Edit mode → 開始第一個任務。

## 8. 每日 workflow

### 早上開工

```bash
git pull
code .
# 在 Claude Code panel:
> /resume   # 接續昨天的對話 (若 Claude Code 版本支援)
# 或開新對話:
> 我要繼續做 Phase X 的 Mx.y。請讀 SPEC 並 review 我上次的 commit。
```

### 任務切換

```bash
# 切換大主題時用 /branch (原 /fork)
> /branch
> 開新任務:做 M3.4 對話 UI
```

這樣不會污染當前任務的 context。

### 收工前

```bash
# 跑全測試
pytest && pnpm test

# 讓 Claude Code 自動產出 commit message
> 請依照 CLAUDE.md 規範,為這次的改動產出一個 commit message,包含:
> - feat/fix/refactor 前綴
> - 模組編號
> - 研究引用
> - RISK 緩解標記
> 不要直接 commit,先讓我看。

# 看過後
git add . && git commit -F .git/COMMIT_EDITMSG
git push
```

## 9. 常見問題

### Q: Claude Code 似乎沒讀 CLAUDE.md

**檢查**:

```bash
ls CLAUDE.md  # 必須在專案根目錄
```

如果在子目錄,Claude Code 找不到。VS Code 必須開啟**整個專案**而不是子資料夾。

### Q: skills 沒被自動觸發

**檢查**:

```bash
ls .claude/skills/
# 應有 cite-research/, audit-integration/, implement-module/

cat .claude/skills/cite-research/SKILL.md | head -5
# 應有 description: 開頭
```

Claude Code 透過 description 來決定何時觸發 skill。如果你的任務描述太模糊,skill 不會自動進入。可主動指定:

```
請使用 cite-research skill,我要為 M4.2 寫 Echo Mode 的程式碼註解
```

### Q: 引用研究時 Claude Code 寫了「根據相關研究」

**這是違反 CLAUDE.md 的**。立刻打斷它:

```
這條註解違反 cite-research skill 的格式要求。請改為 [Rxx: 關鍵字 §章節] 格式,並把它對應的研究找出來。
```

### Q: 任務跨多模組,但 Claude Code 沒做整合風險稽核

立刻打斷:

```
請暫停,先 invoke audit-integration skill。grep docs/05_integration_risk_audit.md 找出此任務涉及的 RISK-xx。
```

### Q: Claude Code 提議跳過寫測試直接 implement

拒絕。引用 `implement-module skill Step 4`:

```
請依 implement-module skill 的 Step 4,先寫測試。Acceptance Criteria 在 SPEC 已定義,直接翻譯成測試。
```

### Q: 想讓 Claude Code 同時改超過一個模組

不建議。但若必須:

```
拆成多個 commit。每個 commit 只動一個 Mx.y。先告訴我順序與依賴。
```

## 10. 進階:Subagent 與並行

當 Phase 5 後專案變大,可以用 subagent 並行:

```
> 用 subagent 並行做兩件事:
> 1. Agent A: 跑全測試並報告失敗
> 2. Agent B: review 最近 5 個 commit 是否符合 CLAUDE.md 規範
>
> 兩者跑完再彙整。
```

subagent 各自有獨立的 context,不會污染主對話。完成後僅回傳摘要。

## 11. Skip-list (絕對不要做的事)

❌ **不要**讓 Claude Code 在 `auto-accept` 模式下處理涉及 RISK 的任務。涉及隱私、Persona、XP 結算的改動必須走 `edit` 模式逐項審批。

❌ **不要**在沒有對應 SPEC 的情況下要 Claude Code 實作模組。它會編造合理但偏離學術的設計。

❌ **不要**為了「節省 token」就刪 CLAUDE.md 內容。它是鐵則,每次 session 必讀。

❌ **不要**在主對話直接做 code review。用 subagent 跑 review,主對話專注實作。

❌ **不要**讓 Claude Code 直接執行 `alembic upgrade head` 在雲端 DB。MVP 階段所有破壞性 migration 必須先在本地 SQLite 驗證。

## 12. 何時你可以暫時不用 Claude Code

- **設計初期的腦力激盪**:用 ChatGPT/Claude 一般版發散
- **隱私敏感對話的內部測試**:本地對話不該過 Claude Code (Anthropic 看得到)
- **小修改 (< 10 行)**:手寫快過讓 LLM 想

但任何涉及多模組整合的任務,**用 Claude Code 並走完七步協議**比手寫快很多且品質更穩。
