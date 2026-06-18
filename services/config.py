"""
M0.3 — 全域設定管理

實作 SPEC: docs/modules/M0_3_env_alembic_SPEC.md §7.1
隱私三層原則: CLAUDE.md §隱私三層原則
— 雲端 credential 全部 optional（Open Question 已拍板）
— 本地模式：僅需 IPAD_AI_LOCAL_HOST + LOCAL_DB_PATH
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


def normalize_ipv6_host(url_or_host: str) -> str:
    if not url_or_host:
        return url_or_host
    scheme = ""
    rest = url_or_host
    if "://" in url_or_host:
        scheme, rest = url_or_host.split("://", 1)
        scheme += "://"
    
    if rest.count(":") > 1:
        if not rest.startswith("["):
            parts = rest.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                ip_part = parts[0]
                port_part = parts[1]
                if ip_part.count(":") > 0:
                    rest = f"[{ip_part}]:{port_part}"
            else:
                rest = f"[{rest}]"
    return scheme + rest


class Settings(BaseSettings):
    """
    coOS 全域配置。
    載入順序: 環境變數 > .env 檔案 > 預設值。
    雲端 credential 全部 optional — 純本地開發時應用可完整啟動。
    """

    # === 邊緣推論 (T1 本地) ===
    ipad_ai_local_host: str = Field(
        default="192.168.0.42:11434",
        description="iPad M1 ai.local 位址（IP:port，不含 scheme）",
    )
    ai_local_host: str = Field(
        default="http://ai.local:11434",
        description="iPad Ollama HTTP 基礎 URL（含 scheme），M2.2/M2.3 直接使用",
    )
    gemma_model: str = Field(
        default="gemma-4-e4b-it-4bit",
        description="Gemma 邊緣模型名稱，對應 Ollama 已載入的模型",
    )

    # === 任務佇列 (T1 本地 Redis) ===
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="arq 任務佇列 Redis 連線 URL（M2.1 離線重試用）",
    )

    # === 雲端 LLM (T3 optional) ===
    gemini_api_key: str = Field(default="", description="Gemini API Key（optional）")
    google_api_key: str = Field(default="", description="Google API Key（optional）")

    # === PostgreSQL @ Supabase (T3 optional) ===
    supabase_url: str = Field(default="", description="Supabase REST URL（optional）")
    supabase_key: str = Field(default="", description="Supabase anon/service key（optional）")
    supabase_db_url: str = Field(default="", description="Supabase PostgreSQL 連線 URL（optional）")

    # === Neo4j AuraDB (T3 optional) ===
    neo4j_uri: str = Field(default="", description="Neo4j 連線 URI（optional）")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="", description="Neo4j 密碼（optional）")

    # === 本地 DB ===
    local_db_path: Path = Field(
        default=Path(__file__).resolve().parent.parent / "data" / "coos.db",
        description="本地 SQLite 路徑",
    )

    # === 使用者識別 (Identity) ===
    current_user_id: str = Field(
        default="00000000-0000-0000-0000-000000000000",
        description="當前使用者 ID。多裝置同步或社群功能開啟後，將改由 Auth Token 取得。",
    )

    # === Google OAuth (L3 identity — multi-device sync) ===
    google_client_id: str = Field(default="", description="Google OAuth Client ID (optional)")
    google_client_secret: str = Field(default="", description="Google OAuth Client Secret (optional)")

    # === 進階 (Phase 6+) ===
    github_client_id: str = Field(default="")
    github_client_secret: str = Field(default="")
    github_webhook_secret: str = Field(default="")
    pollinations_api_secret: str = Field(default="")

    # === 執行期設定 ===
    log_level: str = Field(default="INFO")
    fastapi_port: int = Field(default=8000)
    debug: bool = Field(default=False)

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        # 允許額外欄位（避免 .env 有未定義的 key 時 crash）
        "extra": "ignore",
    }

    @model_validator(mode="after")
    def normalize_hosts(self) -> "Settings":
        self.ipad_ai_local_host = normalize_ipv6_host(self.ipad_ai_local_host)
        self.ai_local_host = normalize_ipv6_host(self.ai_local_host)
        return self


@lru_cache
def get_settings() -> Settings:
    """全域唯一 Settings 實例（FastAPI Depends 注入用）"""
    return Settings()
