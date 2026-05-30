# Phase 0 實作計畫

## Context

Phase 0 的目標是「讓 Claude Code 能在 VS Code 開始幹活」。根據 `docs/06_implementation_phases.md`，Phase 0 的完成定義是：

- [x] git init, .gitignore 建好
- [x] CLAUDE.md + docs/ 全部 commit
- [x] .claude/skills/ 三個 skill 全部建好
- [ ] pnpm + uv 環境，monorepo 結構
- [ ] CI 跑得起來 (pytest + vitest 空殼)
- [ ] 三個 MCP server 在 .mcp.json 配置完成

**驗收標準**：在 VS Code 開啟專案 → Claude Code panel 啟動 → 輸入「請列出所有 MVP 模組」→ 它能回出 24 個模組。

---

## Phase 0 任務清單

### T0-A｜M0.1 — Monorepo 骨架建立

**涉及模組**：M0.1

**研究引用**：無直接學術引用。決策來源為 `docs/02_architecture.md §5` 技術棧固定清單。

**整合風險**：
- 無直接 RISK-xx 觸發
- 次要風險：pnpm + uv 雙 lockfile 互踩 → 緩解：`.gitignore` 分別追蹤，CI 獨立 install

**要做的事**：
1. 建立根目錄 `package.json`（含 `dev`、`test`、`lint` 腳本）
2. 建立 `pnpm-workspace.yaml`（包含 `apps/*`）
3. 建立 `apps/desktop/` Tauri React 應用骨架（`package.json`、`vite.config.ts`、`tsconfig.json`、`src/main.tsx`、`src-tauri/Cargo.toml`、`src-tauri/src/main.rs`、`tauri.conf.json`）
4. 建立 `services/` Python 後端骨架（`pyproject.toml`、`main.py`）
5. 建立 `data/.gitkeep`
6. 建立 `testing/conftest.py`
7. 更新 `.gitignore` 確保涵蓋 `.env`、`*.db`、`node_modules`、`__pycache__`

**驗收測試位置**：`testing/m0_1/test_monorepo_structure.py`（已定義於 SPEC §6）

---

### T0-B｜M0.2 — Tauri IPC 通訊橋骨架

**涉及模組**：M0.2（依賴 M0.1 完成）

**研究引用**：無直接學術引用。決策來源為 `docs/02_architecture.md §1、§7`。

**整合風險**：
- 無直接 RISK-xx 觸發
- 次要風險：FastAPI sidecar 未啟動時前端所有 API 呼叫失敗 → 緩解：`/api/health` 健康檢查端點
- 次要風險：Tauri WebView CSP 阻擋 localhost → 緩解：`tauri.conf.json` 明確允許

**要做的事**：
1. 實作 FastAPI `main.py` 的 `/api/health` 端點 + CORS 中介層（僅允許 `tauri://localhost` 與 `http://localhost:1420`）
2. 實作 Rust `get_system_health` invoke 命令與 sidecar spawn 邏輯
3. 實作前端 `apps/desktop/src/lib/ipc.ts` 抽象層（`rustInvoke`、`apiCall`、`createSSE`）
4. 實作 `/api/m0_2/test_stream` SSE 測試端點（供驗收測試使用）
5. 配置 `tauri.conf.json` 的 CSP 允許 localhost:8000

**驗收測試位置**：`testing/m0_2/test_tauri_ipc.py` + `apps/desktop/src/__tests__/m0_2/test_tauri_invoke.spec.ts`

---

### T0-C｜M0.3 — .env 管理 + Alembic 雙軌設置

**涉及模組**：M0.3（依賴 M0.1 完成）

**研究引用**：無直接學術引用。決策來源為 `docs/02_architecture.md §3、§6.3、§6.4`，以及 `CLAUDE.md §隱私三層原則`。

**整合風險**：
- 無直接 RISK-xx 觸發
- 次要風險：`.env` 意外 commit → 緩解：`.gitignore` + `pre-commit` hook
- 次要風險：Alembic autogenerate 直接 apply 破壞 schema → CLAUDE.md 已明確禁止，必須使用者 review

**要做的事**：
1. 建立 `.env.example`（含所有必要鍵：`GEMINI_API_KEY`、`IPAD_AI_LOCAL_HOST`、`SUPABASE_URL`、`SUPABASE_KEY`、`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`；雲端 credential 全部 optional）
2. 實作 `services/config.py`（Pydantic `BaseSettings`，雲端 credential 設為 optional，`GEMINI_API_KEY` 在純本地模式也可選）
3. 建立 `services/alembic_local.ini`（SQLite 專用）
4. 建立 `services/alembic_cloud.ini`（PostgreSQL 專用）
5. 建立 `services/alembic/env.py`（共用，根據 ini 選 DB URL）
6. 建立 `services/alembic/versions/` 空目錄（`20260530_1200_initial.py` 空 migration）
7. 整合至 `services/main.py` lifespan（啟動驗證）

**驗收測試位置**：`testing/m0_3/test_env_config.py`（已定義於 SPEC §6）

---

### T0-D｜CI 空殼（GitHub Actions）

**涉及模組**：跨 M0.1/M0.2/M0.3

**研究引用**：無。決策來源為 `docs/modules/M0_1_monorepo_SPEC.md §9`（Open Questions 已拍板：GitHub Actions + 快取 + 路徑過濾）。

**整合風險**：無直接 RISK-xx 觸發。

**要做的事**：
1. 建立 `.github/workflows/ci.yml`：
   - 觸發：`push` / `pull_request` 至 `master`
   - 路徑過濾：`services/**`、`apps/**`、`testing/**`
   - Job 1：Python（`uv sync` + `pytest -v testing/`）
   - Job 2：Frontend（`pnpm install` + `pnpm --filter @coos/desktop test`）
   - 快取：`uv` 使用 `actions/cache` 快取 `.venv`；pnpm 使用 `pnpm/action-setup`

---

### T0-E｜MCP Server 配置完成

**涉及模組**：無特定模組，屬 Claude Code 開發環境設定

**研究引用**：無。

**整合風險**：無。

**要做的事**：
1. 檢查現有 `.mcp.json` 內容，確認三個 MCP server（filesystem、sqlite-local、github）是否完整配置
2. 確認 `filesystem` server 的 `allowedDirectories` 涵蓋專案根目錄
3. 確認 `sqlite-local` server 指向正確的 `data/coos.db` 路徑（Phase 1 後才有實際資料，Phase 0 先配置）

---

## 動工順序與依賴關係

```
T0-A (M0.1 Monorepo 骨架)
  ├── T0-B (M0.2 Tauri IPC)   ← 依賴 T0-A
  ├── T0-C (M0.3 .env+Alembic) ← 依賴 T0-A
  └── T0-D (CI)                 ← 依賴 T0-A、T0-B、T0-C
T0-E (MCP 確認)                 ← 獨立，可平行
```

**建議第一個動工的任務：T0-A（M0.1 Monorepo 骨架）**

理由：T0-A 是所有其他任務的基礎，M0.2 與 M0.3 都依賴它定義的目錄結構。且它無研究引用依賴、無整合風險，驗收測試已完整定義於 SPEC §6，可直接開始。

---

## 驗收檢查清單

| 任務 | 測試檔案 | 關鍵驗收條件 |
|------|----------|-------------|
| T0-A | `testing/m0_1/test_monorepo_structure.py` | 6 個 pytest 通過 |
| T0-B | `testing/m0_2/test_tauri_ipc.py` + vitest | `/api/health` 200、SSE 3 events、CORS |
| T0-C | `testing/m0_3/test_env_config.py` | `.env.example` 完整、Alembic upgrade head 成功 |
| T0-D | GitHub Actions 執行 | `pytest -v` + `pnpm test` 綠燈 |
| T0-E | 手動確認 | Claude Code 能列出 24 個 MVP 模組 |
