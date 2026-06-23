# coOS

一款結合多智能體 AI、遊戲化、薩提爾冰山心理模型與邊緣-雲端協同推論的個人目標管理系統。

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
git clone <your-repo-url> coOS
cd coOS

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 填入 GEMINI_API_KEY, NEO4J_*, SUPABASE_* 等

# 5. 啟動後端
cd services
uv run uvicorn main:app --reload

# 6. 啟動前端
cd apps/desktop
pnpm dev

# 7. 在 VS Code 開啟整個資料夾 (不要只開單一檔案)
code .
```

執行後端測試:

```bash
cd services && .venv/Scripts/python.exe -m pytest ../testing/ \
  --ignore=../testing/local_llm --ignore=../testing/m0_2 -q
# 446 passed, 7 skipped
```

## 專案現況 (2026-06-24)

**Phase 5.5 已關閉** — MVP 閉環完整打通。

| 指標 | 數值 |
| ------ | ------ |
| 後端測試 | 446 passed / 0 failed / 7 skipped |
| 完成 Phase | 0 → 1 → 1.5 → 2 → 3 → 4+5 → 5.5 |
| 實作模組數 | M0.4 / M1.1 / M1.2 / M1.4 / M2.1–M2.3 / M3.1–M3.7 / M4.1–M4.6 / M4.13 / M6.1–M6.6 |

### 主要功能

- **多 Persona 對話** (M4.2) — PersonaCard v2 結構化人設、OARS 動機訪談、ClaimLedger 矛盾監控
- **日報閉環** (M3.3 + M4.4.3 + M2.2.2) — 對話 → 邊緣壓縮 → 02:00 自動草稿 → 前端核准
- **社群模組** (M3.7 + M4.13 + M6.6) — XP 質押對賭、公開承諾閉環、挑戰看板
- **遊戲化 XP** (M4.5 + M6.5) — ACID 守門員，`is_reviewed` 確認後才發放
- **隱私三層** — L1 明文本地 SQLite，L2 意圖向量才上雲，L3 業務狀態 PostgreSQL

## 技術棧

| 層 | 技術 |
| -- | ---- |
| 桌面殼 | Tauri 2.x (Rust) |
| 前端 | React + Vite + Zustand + Tailwind + Framer Motion |
| 後端 | Python 3.11+ FastAPI + LangGraph + Pydantic v2 |
| 邊緣推論 | Gemma 4 E4B (4-bit MLX) @ iPad M1 via ai.local |
| 雲端 LLM | Gemini 3.5 Flash / 3.1 Flash Lite |
| 本地 DB | SQLite + SQLAlchemy 2.0 |
| 雲端 DB | PostgreSQL @ Supabase |
| 圖譜 DB | Neo4j AuraDB Free |

## 專案結構

```
coOS/
├── CLAUDE.md                ★ Claude Code 每次 session 必讀
├── .claude/
│   └── skills/              ★ 自訂技能 (audit-integration / cite-research / implement-module)
├── .mcp.json                ★ MCP server 配置
├── docs/
│   ├── 00_README.md         ← 文件地圖
│   ├── 01_product_vision.md
│   ├── 02_architecture.md
│   ├── 03_research_index.md ★ 10 篇研究索引
│   ├── 04_module_registry.md ★ 完整模組登記冊 (子模組+研究+風險)
│   ├── 05_integration_risk_audit.md ★ 整合風險稽核
│   ├── 06_implementation_phases.md
│   ├── CLOSURE_REPORT_PHASE_*.md ← 各 Phase 完成報告
│   └── modules/
│       └── M4_2_persona_state_machine_SPEC.md
├── apps/
│   ├── desktop/             ← Tauri + React 前端
│   ├── browser-extension/   ← Chrome 擴充
│   └── vscode-extension/    ← VS Code 擴充
├── services/                ← FastAPI 後端
│   ├── main.py
│   ├── m0_4_logging/
│   ├── m1_*/                ← 遙測 & 斷點
│   ├── m2_*/                ← Gemma 邊緣推論 & Eguard
│   ├── m4_*/                ← Agent 邏輯核心
│   └── m6_*/                ← 資料層
└── testing/                 ← pytest 測試套件
```

## 授權

待定。
