# Life OS

一款結合多智能體 AI、遊戲化與薩提爾冰山心理模型的個人目標管理系統。

## 給人類

如果你是第一次接觸這個專案,依序讀:

1. `docs/01_product_vision.md` — 5 分鐘了解這是什麼
2. `docs/02_architecture.md` — 15 分鐘了解技術骨架
3. `docs/06_implementation_phases.md` — 5 分鐘了解該做什麼
4. `docs/03_research_index.md` — 略讀,有需要時回查

## 給 Claude Code

開始任何工作前,自動讀 `CLAUDE.md`。已經配置好的 skills 會在你描述任務時自動觸發。

關鍵 grep 路徑:

```bash
grep "M4.2" docs/                       # 找模組相關文件
grep "RISK-" docs/05_integration_risk_audit.md  # 查整合風險
grep "R03" docs/03_research_index.md    # 查研究細節
```

## 給開發者:VS Code 設置 (30 分鐘)

完整步驟見 `docs/SETUP_VSCODE.md`。

簡短版:

```bash
# 1. 安裝 Claude Code CLI
npm install -g @anthropic-ai/claude-code
claude --version

# 2. VS Code 安裝 "Claude Code" extension (publisher: anthropic)

# 3. 取得這個專案
git clone <your-repo-url> lifeos
cd lifeos

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 填入 GEMINI_API_KEY, NEO4J_*, SUPABASE_* 等

# 5. 在 VS Code 開啟整個資料夾 (不要只開單一檔案)
code .

# 6. Cmd/Ctrl+Shift+P → "Claude Code: Open Chat"
# 7. 第一條訊息建議是:
#    「請讀完 CLAUDE.md 與 docs/00_README.md,然後告訴我 Phase 0 該做什麼」
```

## 專案結構

```
lifeos/
├── CLAUDE.md                ★ Claude Code 每次 session 必讀
├── .claude/
│   └── skills/              ★ 三個自訂技能
│       ├── cite-research/
│       ├── audit-integration/
│       └── implement-module/
├── .mcp.json                ★ MCP server 配置
├── docs/
│   ├── 00_README.md         ← 文件地圖
│   ├── 01_product_vision.md
│   ├── 02_architecture.md
│   ├── 03_research_index.md ★ 10 篇研究索引
│   ├── 04_module_research_matrix.md ★ 模組-研究矩陣
│   ├── 05_integration_risk_audit.md ★ 整合風險稽核
│   ├── 06_implementation_phases.md
│   └── modules/
│       ├── _TEMPLATE_SPEC.md
│       └── M4_2_persona_state_machine_SPEC.md ← 範例 SPEC
├── apps/
│   ├── desktop/             ← Tauri 殼
│   └── web/                 ← React 前端
├── services/
│   └── api/                 ← FastAPI 後端
└── tests/
```

## 授權

待定。
