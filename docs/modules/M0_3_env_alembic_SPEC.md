# M0.3 — 環境變數管理與資料庫遷移 (.env + Alembic)

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-05-30

## 1. Purpose (目的)

統一管理所有環境變數 (API key、DB 連線字串、邊緣裝置位址) 的載入與驗證,並透過 Alembic 管理本地 SQLite 與雲端 PostgreSQL 的 schema 版本遷移,確保任何環境 (開發 / CI / 生產) 下資料庫結構都可被可重現地升降級。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| (無) | 架構文件 §3 隱私三層分類 | 環境變數中的雲端 credential 必須嚴格分層管理 |
| (無) | 架構文件 §6.3 環境變數 | `.env` 的鍵值定義源於此 |
| (無) | 架構文件 §6.4 資料庫遷移 | 雙 alembic.ini (local + cloud) 的設計來源 |

> 本模組屬基礎設施,無直接學術研究引用。所有決策來自 `02_architecture.md` 與 `CLAUDE.md §隱私三層原則`。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| `.env` 檔案 | Key=Value 純文字 | `GEMINI_API_KEY=AIza...` |
| `.env.example` | 模板 (無機密值) | `GEMINI_API_KEY=` |
| `services/alembic/versions/*.py` | Alembic migration scripts | `001_create_raw_tracking_logs.py` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `services/config.py` | Pydantic `BaseSettings` | `Settings(gemini_api_key="AIza...")` |
| 本地 SQLite schema | 資料表 | `data/coos.db` 中的 `raw_tracking_logs` |
| 雲端 PostgreSQL schema | 資料表 | Supabase 中的 `users`, `ai_experts` |
| 驗證錯誤 | `ValidationError` | 啟動時若 `GEMINI_API_KEY` 為空則 crash |

### 環境變數分類

```
┌─────────────────────────────────────────────────────┐
│ 隱私層級 T1 — 絕不上雲的 credential                │
│   (這些只影響本地連線,不應出現在雲端服務的環境中)  │
│   IPAD_AI_LOCAL_HOST=192.168.0.42:11434             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 隱私層級 T3 — 雲端服務 credential                   │
│   GEMINI_API_KEY=...                                │
│   SUPABASE_URL=...                                  │
│   SUPABASE_KEY=...                                  │
│   NEO4J_URI=...                                     │
│   NEO4J_USER=...                                    │
│   NEO4J_PASSWORD=...                                │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 進階 — 非 MVP 必要                                  │
│   GITHUB_CLIENT_ID=...                              │
│   GITHUB_CLIENT_SECRET=...                          │
│   POLLINATIONS_API_SECRET=...                       │
└─────────────────────────────────────────────────────┘
```

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.1** (Monorepo):依賴 `services/` 目錄結構存在,以放置 `config.py` 與 `alembic/`

### 下游 (誰依賴我)

- **M0.4** (結構化日誌):依賴 `config.py` 中的 `LOG_LEVEL` 設定
- **M6.1** (SQLite schemas):依賴 Alembic 遷移來建立資料表
- **M6.2** (PostgreSQL):依賴 Alembic 遷移 + `SUPABASE_URL` 環境變數
- **M2.2** (Gemma 邊緣推論):依賴 `IPAD_AI_LOCAL_HOST` 環境變數
- **所有呼叫雲端 API 的模組**:依賴 `GEMINI_API_KEY`, `NEO4J_*` 等

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| (無直接 RISK-xx) | `.env` 被意外 commit → 雲端 credential 洩漏 | `.gitignore` 中 `.env` 已排除; CI 中使用 `git-secrets` 掃描; `pre-commit` hook 檢查 |
| (無直接 RISK-xx) | Alembic `--autogenerate` 直接 apply 產生破壞性 migration | CLAUDE.md 已明確禁止自動 apply; 必須先讓使用者 review migration 內容 |
| (無直接 RISK-xx) | 本地 SQLite 與雲端 PostgreSQL 的 migration 版本不同步 | 雙 alembic.ini 各自維護版本線; `alembic current` 在 CI 中同時檢查兩個 |

> 已 grep `05_integration_risk_audit.md`,無 RISK-xx 與 M0.3 直接相關。

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m0_3/test_env_config.py

import os
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class TestEnvLoading:
    def test_env_example_exists():
        """驗收條件 1: .env.example 模板存在且包含所有必要鍵"""
        env_example = PROJECT_ROOT / ".env.example"
        assert env_example.exists()
        content = env_example.read_text()
        required_keys = [
            "GEMINI_API_KEY",
            "IPAD_AI_LOCAL_HOST",
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "NEO4J_URI",
            "NEO4J_USER",
            "NEO4J_PASSWORD",
        ]
        for key in required_keys:
            assert key in content, f".env.example 缺少 {key}"

    def test_settings_loads_from_env(monkeypatch):
        """驗收條件 2: Pydantic Settings 能從環境變數載入"""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key_123")
        monkeypatch.setenv("IPAD_AI_LOCAL_HOST", "192.168.0.42:11434")
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "test_supabase_key")
        monkeypatch.setenv("NEO4J_URI", "neo4j+s://test.neo4j.io")
        monkeypatch.setenv("NEO4J_USER", "neo4j")
        monkeypatch.setenv("NEO4J_PASSWORD", "test_password")

        from services.config import Settings
        settings = Settings()
        assert settings.gemini_api_key == "test_key_123"
        assert settings.ipad_ai_local_host == "192.168.0.42:11434"

    def test_missing_required_env_raises(monkeypatch):
        """驗收條件 3: 缺少必要環境變數時 Settings 拋出 ValidationError"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        from pydantic import ValidationError
        from services.config import Settings
        with pytest.raises(ValidationError):
            Settings()

    def test_env_not_in_git():
        """驗收條件 4: .env 不在 Git 追蹤中"""
        gitignore = (PROJECT_ROOT / ".gitignore").read_text()
        assert ".env" in gitignore


class TestAlembicSetup:
    def test_alembic_local_ini_exists():
        """驗收條件 5: 本地 SQLite 的 alembic 配置存在"""
        assert (PROJECT_ROOT / "services" / "alembic_local.ini").exists()

    def test_alembic_cloud_ini_exists():
        """驗收條件 6: 雲端 PostgreSQL 的 alembic 配置存在"""
        assert (PROJECT_ROOT / "services" / "alembic_cloud.ini").exists()

    def test_alembic_versions_directory_exists():
        """驗收條件 7: Alembic versions 目錄存在"""
        versions_dir = PROJECT_ROOT / "services" / "alembic" / "versions"
        assert versions_dir.exists()
        assert versions_dir.is_dir()

    def test_alembic_local_can_upgrade(tmp_path):
        """驗收條件 8: Alembic 能對空 SQLite 執行 upgrade head"""
        import subprocess
        db_path = tmp_path / "test.db"
        result = subprocess.run(
            ["alembic", "-c", "alembic_local.ini", "upgrade", "head"],
            cwd=str(PROJECT_ROOT / "services"),
            env={**os.environ, "LOCAL_DB_PATH": str(db_path)},
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Alembic upgrade 失敗: {result.stderr}"
```

## 7. Implementation Notes

### 7.1 Pydantic Settings 設計

```python
# services/config.py

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    """
    coOS 全域配置。
    載入順序: 環境變數 > .env 檔案 > 預設值。
    """

    # === Cloud LLM ===
    gemini_api_key: str = Field(..., description="Gemini 3.5 Pro API Key")

    # === Edge Inference ===
    ipad_ai_local_host: str = Field(
        default="192.168.0.42:11434",
        description="iPad M1 ai.local 位址"
    )

    # === Cloud DB (PostgreSQL @ Supabase) ===
    supabase_url: str = Field(..., description="Supabase REST URL")
    supabase_key: str = Field(..., description="Supabase anon/service key")

    # === Graph DB (Neo4j AuraDB) ===
    neo4j_uri: str = Field(..., description="Neo4j 連線 URI")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(..., description="Neo4j 密碼")

    # === Local DB ===
    local_db_path: Path = Field(
        default=Path("../data/coos.db"),
        description="本地 SQLite 路徑 (相對於 services/)"
    )

    # === 進階 (非 MVP 必要) ===
    github_client_id: str = Field(default="", description="OAuth (進階)")
    github_client_secret: str = Field(default="", description="OAuth (進階)")
    pollinations_api_secret: str = Field(default="", description="生圖 API")

    # === 運行時設定 ===
    log_level: str = Field(default="INFO")
    fastapi_port: int = Field(default=8000)
    debug: bool = Field(default=False)

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("GEMINI_API_KEY 不可為空")
        return v

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """全域唯一 Settings 實例 (FastAPI Depends 注入用)"""
    return Settings()
```

### 7.2 Alembic 雙軌配置

```
services/
├── alembic_local.ini      ← SQLite 專用
├── alembic_cloud.ini      ← PostgreSQL 專用
└── alembic/
    ├── env.py             ← 共用,根據 config 選擇 DB URL
    ├── script.py.mako
    └── versions/
        ├── 001_create_raw_tracking_logs.py
        ├── 002_create_edge_event_buffer.py
        └── ...
```

**`alembic_local.ini` 重點**:

```ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///%(LOCAL_DB_PATH)s

# SQLite 特殊設定
[alembic:exclude]
tables = alembic_version
```

**`alembic_cloud.ini` 重點**:

```ini
[alembic]
script_location = alembic
# URL 由環境變數注入,不寫死
sqlalchemy.url = %(SUPABASE_DB_URL)s
```

### 7.3 `env.py` 共用邏輯

```python
# services/alembic/env.py

from alembic import context
from sqlalchemy import engine_from_config, pool
from services.config import get_settings
import os

def run_migrations_online():
    settings = get_settings()
    config = context.config

    # 根據啟動的 ini 檔決定 DB URL
    url = config.get_main_option("sqlalchemy.url")
    if "%(LOCAL_DB_PATH)s" in url:
        url = url.replace("%(LOCAL_DB_PATH)s", str(settings.local_db_path))
    if "%(SUPABASE_DB_URL)s" in url:
        url = os.environ.get("SUPABASE_DB_URL", settings.supabase_url)

    connectable = engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

### 7.4 啟動時驗證流程

```python
# services/main.py (FastAPI lifespan)

from contextlib import asynccontextmanager
from services.config import get_settings

@asynccontextmanager
async def lifespan(app):
    # 啟動時驗證所有必要環境變數
    settings = get_settings()  # 若缺必要變數,這裡直接 crash

    # 驗證本地 SQLite 可存取
    assert settings.local_db_path.parent.exists(), \
        f"data/ 目錄不存在: {settings.local_db_path.parent}"

    # 驗證邊緣裝置可達 (非阻塞, 僅警告)
    if not await ping_edge_device(settings.ipad_ai_local_host):
        logger.warning("[M0.3] iPad ai.local 不可達,邊緣推論將退化")

    yield  # 應用運行中

    # 關閉時清理
    logger.info("[M0.3] 應用關閉,清理連線")
```

### 7.5 異常處理

- `.env` 檔案不存在 → Pydantic Settings 退化為純環境變數讀取; 若必要變數缺失則 `ValidationError` crash
- Alembic migration 衝突 (兩人同時建立 migration) → `alembic merge heads` 合併分支
- SQLite 檔案鎖定 (另一進程佔用) → 重試 3 次,間隔 500ms; 超過則 log 錯誤並退出
- PostgreSQL 連線失敗 → 啟動不 crash (雲端 DB 對 MVP 本地開發非必要),但 log `WARNING`

## 8. Anti-patterns (反模式)

- ❌ **不要在程式碼中硬編碼任何 API key、密碼或連線字串**。所有機密值必須來自環境變數。
  理由:CLAUDE.md 隱私三層原則; 硬編碼一旦 commit 即永久暴露於 Git 歷史。

- ❌ **不要執行 `alembic revision --autogenerate` 後直接 `alembic upgrade head`**。必須先讓使用者 review 產生的 migration 腳本。
  理由:CLAUDE.md 明確禁止; autogenerate 可能產生破壞性 DROP 操作。

- ❌ **不要建立單一 `alembic.ini` 同時管理 SQLite 和 PostgreSQL**。必須分為 `alembic_local.ini` 和 `alembic_cloud.ini`。
  理由:SQLite 與 PostgreSQL 的 DDL 語法差異 (例如 `ALTER TABLE` 限制) 會導致同一 migration 在不同 DB 上失敗。

- ❌ **不要在 Settings 中設定 `env_file = ".env"` 的相對路徑時假設 CWD**。使用相對於 `services/` 的 `"../.env"` 或絕對路徑。
  理由:Tauri sidecar spawn 時 CWD 可能不是專案根目錄。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [ ] **MVP 階段是否所有雲端 credential 都設為 optional?** 純本地開發時 (無 Supabase / Neo4j),是否允許啟動並只使用 SQLite? 還是強制要求所有 credential 都填?
- [ ] **Alembic migration 檔名是否帶時間戳?** (`alembic revision --rev-id` 的格式: 流水號 `001` vs 時間戳 `20260530_1200`)
- [ ] **是否需要 `alembic downgrade` 的自動化腳本?** 或者 downgrade 永遠由使用者手動執行?

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 無學術研究引用,已明確標註屬基礎設施
- [x] §3 Schema 用 Pydantic / INI / 環境變數分類圖描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,無直接對應 RISK
- [x] §6 測試先於程式碼
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
