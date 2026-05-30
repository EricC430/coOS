"""
M0.1 Monorepo 結構驗收測試
對應 docs/modules/M0_1_monorepo_SPEC.md §6
"""
import re
from pathlib import Path

import yaml

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
    with open(PROJECT_ROOT / "pnpm-workspace.yaml") as f:
        config = yaml.safe_load(f)
    packages = config.get("packages", [])
    assert "apps/*" in packages or "apps/desktop" in packages


def test_module_naming_convention():
    """驗收條件 5: services/ 下的子目錄遵循 mX_Y_name 命名規則

    例外（框架強制固定名稱，不可重命名）:
      - alembic/  — Alembic 工具要求的固定目錄名
      - .venv/    — uv virtualenv
    """
    # 框架強制固定名稱，不受模組命名規則約束
    FRAMEWORK_DIRS = {"alembic", "alembic_cloud", ".venv", "__pycache__"}

    services_dir = PROJECT_ROOT / "services"
    if services_dir.exists():
        for child in services_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name.startswith(("_", ".", "__")):
                continue
            if child.name in FRAMEWORK_DIRS:
                continue
            assert re.match(r"m\d+_\d+_\w+", child.name), (
                f"目錄 {child.name} 不符合 mX_Y_name 命名規則"
            )


def test_gitignore_covers_secrets():
    """驗收條件 6: .gitignore 必須排除 .env 與敏感檔案"""
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    assert "*.db" in gitignore or "data/" in gitignore
