"""
M0.3 環境變數管理與 Alembic 雙軌設置驗收測試
對應 docs/modules/M0_3_env_alembic_SPEC.md §6

NOTE: 雲端 credential 全部 optional (Open Question 已拍板)。
      測試 3 驗證缺少 GEMINI_API_KEY 時仍可啟動（本地開發模式）。
"""
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "services"


# ---------------------------------------------------------------------------
# 驗收條件 1 — .env.example 存在且含必要鍵
# ---------------------------------------------------------------------------

def test_env_example_exists():
    """驗收條件 1: .env.example 模板存在且包含所有必要鍵"""
    env_example = PROJECT_ROOT / ".env.example"
    assert env_example.exists(), ".env.example 不存在"
    content = env_example.read_text(encoding="utf-8")
    required_keys = [
        "GEMINI_API_KEY",
        "IPAD_AI_LOCAL_HOST",
        "SUPABASE_URL",
        "SUPABASE_DB_URL",   # Phase 1.5: renamed from SUPABASE_KEY to SUPABASE_DB_URL
        "NEO4J_URI",
        "NEO4J_USER",
        "NEO4J_PASSWORD",
    ]
    for key in required_keys:
        assert key in content, f".env.example 缺少 {key}"


# ---------------------------------------------------------------------------
# 驗收條件 2 — Pydantic Settings 從環境變數載入
# ---------------------------------------------------------------------------

def test_settings_loads_from_env(monkeypatch):
    """驗收條件 2: Pydantic Settings 能從環境變數載入"""
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_123")
    monkeypatch.setenv("IPAD_AI_LOCAL_HOST", "192.168.0.42:11434")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test_supabase_key")
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://test.neo4j.io")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test_password")

    import importlib
    import sys
    # services/ 加入 path 讓測試可直接匯入
    sys.path.insert(0, str(SERVICES_DIR))
    import config as cfg_mod
    importlib.reload(cfg_mod)

    settings = cfg_mod.Settings(_env_file=None)
    assert settings.gemini_api_key == "test_key_123"
    assert settings.ipad_ai_local_host == "192.168.0.42:11434"


# ---------------------------------------------------------------------------
# 驗收條件 3 — 缺少 GEMINI_API_KEY 時仍可啟動（雲端 optional）
# ---------------------------------------------------------------------------

def test_settings_works_without_cloud_keys(monkeypatch):
    """驗收條件 3: 雲端 credential 全部 optional，本地模式可啟動"""
    # 清除所有雲端 credential
    for key in ["GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY",
                "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]:
        monkeypatch.delenv(key, raising=False)

    import importlib
    import sys
    sys.path.insert(0, str(SERVICES_DIR))
    import config as cfg_mod
    importlib.reload(cfg_mod)

    # _env_file=None 確保不讀取磁碟上的 .env，只看已 monkeypatch 的環境變數
    settings = cfg_mod.Settings(_env_file=None)
    assert settings.gemini_api_key == ""
    assert settings.ipad_ai_local_host == "192.168.0.42:11434"


# ---------------------------------------------------------------------------
# 驗收條件 4 — .env 不在 Git 追蹤中
# ---------------------------------------------------------------------------

def test_env_not_in_git():
    """驗收條件 4: .env 不在 Git 追蹤中（.gitignore 已排除）"""
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore


# ---------------------------------------------------------------------------
# 驗收條件 5 & 6 — Alembic 雙軌 ini 存在
# ---------------------------------------------------------------------------

def test_alembic_local_ini_exists():
    """驗收條件 5: 本地 SQLite 的 alembic 配置存在"""
    assert (SERVICES_DIR / "alembic_local.ini").exists()


def test_alembic_cloud_ini_exists():
    """驗收條件 6: 雲端 PostgreSQL 的 alembic 配置存在"""
    assert (SERVICES_DIR / "alembic_cloud.ini").exists()


# ---------------------------------------------------------------------------
# 驗收條件 7 — Alembic versions 目錄存在
# ---------------------------------------------------------------------------

def test_alembic_versions_directory_exists():
    """驗收條件 7: Alembic versions 目錄存在"""
    versions_dir = SERVICES_DIR / "alembic" / "versions"
    assert versions_dir.exists()
    assert versions_dir.is_dir()


# ---------------------------------------------------------------------------
# 驗收條件 8 — Alembic upgrade head 對空 SQLite 成功
# ---------------------------------------------------------------------------

def test_alembic_local_can_upgrade(tmp_path):
    """驗收條件 8: Alembic 能對空 SQLite 執行 upgrade head"""
    db_path = tmp_path / "test_upgrade.db"
    env = {
        **os.environ,
        "LOCAL_DB_PATH": str(db_path),
        # 清除雲端 credential 避免 Pydantic 載入失敗
        "GEMINI_API_KEY": "",
        "SUPABASE_URL": "",
        "SUPABASE_KEY": "",
        "NEO4J_URI": "",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "",
    }
    result = subprocess.run(
        ["uv", "run", "alembic", "-c", "alembic_local.ini", "upgrade", "head"],
        cwd=str(SERVICES_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Alembic upgrade 失敗:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
