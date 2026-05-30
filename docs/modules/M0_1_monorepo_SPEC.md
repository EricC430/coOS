# M0.1 — Monorepo 專案結構 (Monorepo Project Structure)

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-05-30

## 1. Purpose (目的)

建立統一的 Monorepo 專案目錄結構,使前端 (Tauri/React)、後端 (FastAPI)、邊緣推論 (ai.local 客戶端) 三個 workspace 共存於單一 Git 倉庫,並透過 `pnpm` (Node) + `uv` (Python) 雙套件管理器實現一致的依賴安裝與腳本執行體驗。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| (無) | 架構文件 §5 技術棧固定清單 | 前後端技術棧組合決定 Monorepo 內部結構 |
| (無) | 架構文件 §6 開發環境 | `pnpm dev` + `uvicorn` 雙啟動命令源於此 |

> 本模組屬基礎設施,無直接學術研究引用。所有決策來自 `02_architecture.md` 與 `CLAUDE.md`。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| 人類開發者 / Claude Code | CLI 命令 | `pnpm install`, `uv sync` |
| `02_architecture.md` §5 | 固定技術棧清單 | React 18, FastAPI 0.110.*, Tauri 2.x |
| `.env.example` | 環境變數模板 | `GEMINI_API_KEY=...` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| 專案目錄結構 | 檔案系統 | 見 §7.2 目錄樹 |
| `pnpm-workspace.yaml` | YAML | `packages: ['apps/*', 'packages/*']` |
| `pyproject.toml` (後端) | TOML | `[project] name = "coos-backend"` |
| 根目錄 `package.json` | JSON | Monorepo 根腳本 (`dev`, `test`, `lint`) |

## 4. Dependencies

### 上游 (我依賴誰)

- 無。M0.1 是所有模組的最底層基礎。

### 下游 (誰依賴我)

- **M0.2** (Tauri IPC):依賴 Monorepo 結構中 `apps/desktop/src-tauri/` 的存在
- **M0.3** (.env + Alembic):依賴 Monorepo 結構中 `services/` 與 `alembic/` 的路徑
- **M0.4** (結構化日誌):依賴 `services/m0_4_logging/` 目錄
- **所有其他模組**:依賴 M0.1 定義的命名規則 (`services/mX_Y_name/`, `apps/web/src/components/mX_Y_name/`)

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| (無直接 RISK-xx) | pnpm + uv 雙套件管理器互踩 lockfile | 根目錄 `.gitignore` 分別追蹤 `pnpm-lock.yaml` 與 `uv.lock`; CI 中兩者獨立 install |
| (無直接 RISK-xx) | Tauri 2.x Rust 編譯時間過長拖慢 CI | Rust 編譯步驟加入 `sccache` 快取; 本地開發使用 `cargo check` 替代 full build |

> 已 grep `05_integration_risk_audit.md`,無 RISK-xx 與 M0.1 直接相關。

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m0_1/test_monorepo_structure.py

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def test_monorepo_root_files_exist():
    """驗收條件 1: 根目錄必要檔案存在"""
    required = [
        "package.json",
        "pnpm-workspace.yaml",
        ".gitignore",
        "CLAUDE.md",
        "README.md",
    ]
    for f in required:
        assert (PROJECT_ROOT / f).exists(), f"缺少根目錄檔案: {f}"

def test_frontend_workspace_exists():
    """驗收條件 2: 前端 Tauri workspace 結構完整"""
    assert (PROJECT_ROOT / "apps" / "desktop" / "package.json").exists()
    assert (PROJECT_ROOT / "apps" / "desktop" / "src-tauri" / "Cargo.toml").exists()
    assert (PROJECT_ROOT / "apps" / "desktop" / "src" / "main.tsx").exists()

def test_backend_workspace_exists():
    """驗收條件 3: 後端 Python workspace 結構完整"""
    assert (PROJECT_ROOT / "services" / "pyproject.toml").exists()
    assert (PROJECT_ROOT / "services" / "main.py").exists()

def test_pnpm_workspace_config():
    """驗收條件 4: pnpm-workspace.yaml 包含前端 workspace"""
    import yaml
    with open(PROJECT_ROOT / "pnpm-workspace.yaml") as f:
        config = yaml.safe_load(f)
    assert "apps/*" in config.get("packages", []) or \
           "apps/desktop" in config.get("packages", [])

def test_module_naming_convention():
    """驗收條件 5: services/ 下的子目錄遵循 mX_Y_name 命名規則"""
    import re
    services_dir = PROJECT_ROOT / "services"
    if services_dir.exists():
        for child in services_dir.iterdir():
            if child.is_dir() and not child.name.startswith(("_", ".")):
                assert re.match(r"m\d+_\d+_\w+", child.name), \
                    f"目錄 {child.name} 不符合 mX_Y_name 命名規則"

def test_gitignore_covers_secrets():
    """驗收條件 6: .gitignore 必須排除 .env 與敏感檔案"""
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()
    assert ".env" in gitignore
    assert "*.db" in gitignore or "data/" in gitignore
```

## 7. Implementation Notes

### 7.1 套件管理器選型

| 層 | 套件管理器 | 理由 |
| -- | ---------- | ---- |
| 前端 (React/Tauri) | **pnpm** | 硬連結節省磁碟; Monorepo 原生支援 workspace |
| 後端 (FastAPI) | **uv** | 極快的 Python 依賴解析 (比 pip 快 10-100x); lockfile 確保可重現 |
| Rust (Tauri core) | **cargo** | Tauri 2.x 原生; 無替代品 |

### 7.2 目錄結構

```
coOS/
├── .claude/skills/              ← Claude Code skills (已存在)
├── .env                         ← 環境變數 (不 commit)
├── .env.example                 ← 模板 (commit)
├── .gitignore
├── .mcp.json                    ← MCP server 配置 (已存在)
├── CLAUDE.md                    ← 鐵則 (已存在)
├── README.md
├── package.json                 ← Monorepo 根 (scripts: dev, test, lint)
├── pnpm-workspace.yaml          ← pnpm workspace 定義
│
├── apps/
│   └── desktop/                 ← Tauri 2.x 前端
│       ├── package.json         ← React + Vite + Zustand + Tailwind
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── src/
│       │   ├── main.tsx
│       │   ├── App.tsx
│       │   └── components/
│       │       └── m3_2_dashboard/  ← 依模組命名
│       └── src-tauri/
│           ├── Cargo.toml       ← Tauri + tokio + sqlx
│           ├── src/
│           │   └── main.rs
│           └── tauri.conf.json
│
├── services/                    ← Python 後端 (FastAPI sidecar)
│   ├── pyproject.toml           ← uv 管理的依賴
│   ├── main.py                  ← FastAPI 入口
│   ├── alembic/                 ← DB migration (→ M0.3)
│   ├── m4_1_router/             ← 模組子目錄
│   ├── m4_2_persona/
│   └── ...
│
├── data/                        ← 本地資料 (不 commit, .gitkeep 佔位)
│   ├── .gitkeep
│   └── coos.db                ← SQLite (runtime 產生)
│
├── docs/                        ← 設計文件 (已存在)
│   └── modules/
│
└── testing/                     ← 測試根目錄
    ├── conftest.py
    ├── m0_1/
    ├── m4_2/
    └── ...
```

### 7.3 根目錄 `package.json` 腳本定義

```json
{
  "name": "coos",
  "private": true,
  "scripts": {
    "dev": "pnpm --filter @coos/desktop dev",
    "dev:backend": "uv run --directory services uvicorn main:app --reload --port 8000",
    "dev:all": "concurrently \"pnpm dev\" \"pnpm dev:backend\"",
    "test": "pnpm --filter @coos/desktop test && uv run --directory services pytest -v",
    "lint": "pnpm --filter @coos/desktop lint && uv run --directory services ruff check ."
  }
}
```

### 7.4 異常處理

- `pnpm install` 失敗 → 檢查 Node.js ≥ 18; 清除 `node_modules` 後重試
- `uv sync` 失敗 → 檢查 Python ≥ 3.11; 確認 `uv` 已安裝
- `cargo build` 失敗 → 確認 Rust toolchain 已安裝 (`rustup show`)

## 8. Anti-patterns (反模式)

- ❌ **不要在根目錄直接放 Python 原始碼**。所有 Python 模組必須在 `services/` 下,以 `mX_Y_name/` 命名。
  理由:根目錄混放會破壞 `uv` workspace 隔離,且讓 `grep` 範圍失控。

- ❌ **不要使用 `npm` 或 `yarn` 替代 `pnpm`**。
  理由:技術棧固定清單 (`02_architecture.md §5`) 已鎖定 pnpm; 混用會產生兩份 lockfile。

- ❌ **不要把 `data/coos.db` 或 `.env` commit 進 Git**。
  理由:`.env` 含 API key; `coos.db` 含 L1 明文資料 (隱私三層原則)。

- ❌ **不要在 `services/` 下建立不帶模組編號前綴的目錄** (例如 `services/utils/`)。
  理由:CLAUDE.md 命名規範要求所有子目錄帶 `mX_Y_` 前綴。共用工具放 `services/_shared/`。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [x] **Monorepo 是否引入 Turborepo 或 Nx 做 build orchestration?** 還是 pnpm workspace + 手動 scripts 就夠? (決策：MVP 階段先使用 pnpm workspace + 手動 scripts 即可)
- [x] **`testing/` 目錄是否統一放在根目錄,還是各 workspace 各自放?** (決策：統一放在根目錄，底下依模組與架構分層結構)
- [x] **CI 系統用 GitHub Actions 還是其他?** (決策：使用 GitHub Actions，採用快取與路徑過濾機制以節省每月額度)

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 無學術研究引用,已明確標註屬基礎設施
- [x] §3 Schema 用具體檔案格式描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,無直接對應 RISK
- [x] §6 測試先於程式碼
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
