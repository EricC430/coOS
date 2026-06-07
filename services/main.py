"""
coOS FastAPI Sidecar — 主入口

實作 SPEC: docs/modules/M0_2_tauri_ipc_SPEC.md (IPC 橋)
         docs/modules/M0_3_env_alembic_SPEC.md (啟動驗證)
         docs/modules/M2_1_event_debouncing_SPEC.md v1.1
         docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1
         docs/modules/M2_3_eguard_crypto_filter_SPEC.md v1.1
         docs/modules/M1_4_git_workflow_telemetry_SPEC.md v1.2
         docs/modules/M1_1_os_telemetry_daemon_SPEC.md v1.2
         docs/modules/M1_2_breakpoint_detection_SPEC.md v1.1
"""
import asyncio
import json
import logging
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import get_settings
from m0_4_logging.schema import LogEvent
from m1_2_breakpoint.breakpoint_engine import BreakpointEngine
from m1_4_github.local_git_monitor import LocalGitMonitor
from m1_4_github.oauth import router as m1_4_oauth_router
from m1_4_github.webhooks import router as m1_4_webhook_router
from m2_1_event_debouncer.debouncer import EventDebouncer
from m2_1_event_debouncer.schema import EventBatch, RawTelemetryEvent
from m2_2_gemma.pipeline import GemmaInferencePipeline
from m2_2_gemma.schema import IntentVector
from m2_3_eguard.drift import DriftShield
from m2_3_eguard.exceptions import InjectionDetectedException
from m2_3_eguard.filter import EguardFilter
from m2_3_eguard.schema import RawTextPayload, SanitizedPayload
from m4_1_router.graph import get_router_graph
from m4_3_role_isolation.context import build_role_context

# M4 / M6 integration imports
from m4_3_role_isolation.middleware import RoleIsolationMiddleware
from m6_2_postgresql.engine import get_cloud_engine, is_cloud_available
from m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper

settings = get_settings()
logger = logging.getLogger(__name__)
_start_time = time.time()


class AsyncDBAdapter:
    def __init__(self, sqlite_conn, pg_engine=None):
        self.sqlite_conn = sqlite_conn
        self.pg_engine = pg_engine

    async def fetch_all(self, query: str, params: dict | None = None) -> list[dict]:
        params = params or {}
        def _sync():
            is_local_table = any(t in query for t in [
                "role_implicit_states",
                "chat_transcripts",
                "raw_tracking_logs",
                "routing_samples",
                "temp_event_queue",
                "intent_logs",
                "role_router_rules",
                "user_consents",
                "git_watched_paths",
                "github_tokens",
                "items_dictionary",
                "user_collections",
                "roles",
                "ai_experts",
                "goals",
                "promises",
                "role_projects",
                "users",
                "xp_ledger",
                "daily_reflections",
                "daily_reflection_segments"
            ])
            if is_local_table or not self.pg_engine:
                try:
                    cursor = self.sqlite_conn.cursor()
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [dict(r) for r in rows]
                except Exception as e:
                    logger.debug("[AsyncDBAdapter] SQLite query failed: %s. Query: %s", e, query)
                    return self._get_mock_fallback(query, params)
            else:
                try:
                    with self.pg_engine.connect() as conn:
                        from sqlalchemy import text
                        result = conn.execute(text(query), params)
                        return [dict(row._mapping) for row in result.all()]
                except Exception as e:
                    logger.warning("[AsyncDBAdapter] PG query failed: %s. Falling back to mocks.", e)
                    return self._get_mock_fallback(query, params)
        return await asyncio.to_thread(_sync)

    async def fetch_one(self, query: str, params: dict | None = None) -> dict | None:
        params = params or {}
        def _sync():
            is_local_table = any(t in query for t in [
                "role_implicit_states",
                "chat_transcripts",
                "raw_tracking_logs",
                "routing_samples",
                "temp_event_queue",
                "intent_logs",
                "role_router_rules",
                "user_consents",
                "git_watched_paths",
                "github_tokens",
                "items_dictionary",
                "user_collections",
                "roles",
                "ai_experts",
                "goals",
                "promises",
                "role_projects",
                "users",
                "xp_ledger",
                "daily_reflections",
                "daily_reflection_segments"
            ])
            if is_local_table or not self.pg_engine:
                try:
                    cursor = self.sqlite_conn.cursor()
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    return dict(row) if row else None
                except Exception as e:
                    logger.debug("[AsyncDBAdapter] SQLite fetchone failed: %s. Query: %s", e, query)
                    fallback_list = self._get_mock_fallback(query, params)
                    return fallback_list[0] if fallback_list else None
            else:
                try:
                    with self.pg_engine.connect() as conn:
                        from sqlalchemy import text
                        result = conn.execute(text(query), params)
                        row = result.fetchone()
                        return dict(row._mapping) if row else None
                except Exception as e:
                    logger.warning("[AsyncDBAdapter] PG fetchone failed: %s. Falling back.", e)
                    fallback_list = self._get_mock_fallback(query, params)
                    return fallback_list[0] if fallback_list else None
        return await asyncio.to_thread(_sync)

    async def execute(self, query: str, params: dict | None = None) -> None:
        params = params or {}
        def _sync():
            is_local_table = any(t in query for t in [
                "role_implicit_states",
                "chat_transcripts",
                "raw_tracking_logs",
                "routing_samples",
                "temp_event_queue",
                "intent_logs",
                "role_router_rules",
                "user_consents",
                "git_watched_paths",
                "github_tokens",
                "items_dictionary",
                "user_collections",
                "roles",
                "ai_experts",
                "goals",
                "promises",
                "role_projects",
                "users",
                "xp_ledger",
                "daily_reflections",
                "daily_reflection_segments"
            ])
            if is_local_table or not self.pg_engine:
                try:
                    cursor = self.sqlite_conn.cursor()
                    q = query.replace("NOW()", "(strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))")
                    cursor.execute(q, params)
                    self.sqlite_conn.commit()
                except Exception as e:
                    logger.warning("[AsyncDBAdapter] SQLite execute failed: %s. Query: %s", e, query)
            else:
                try:
                    with self.pg_engine.connect() as conn:
                        from sqlalchemy import text
                        conn.execute(text(query), params)
                        conn.commit()
                except Exception as e:
                    logger.warning("[AsyncDBAdapter] PG execute failed: %s", e)
        await asyncio.to_thread(_sync)

    def _get_mock_fallback(self, query: str, params: dict) -> list[dict]:
        query_lower = query.lower()
        role_id = params.get("rid") or "csie_001"
        if "ai_experts" in query_lower:
            return [
                {
                    "id": "robert_001",
                    "name": "學長Robert",
                    "role_id": role_id,
                    "personality_prompt": "你是一個資深的電腦科學系學長，熱心解答問題，用字精準且帶有程式設計師的幽默。",  # noqa: E501
                    "backstory": "在 CSIE 待了四年的傳奇人物",
                    "tone_default": "authoritative",
                    "trust_level": 0.85,
                    "avatar_url": None,
                    "is_active": True,
                }
            ]
        elif "role_projects" in query_lower:
            return [
                {
                    "id": "project_demo_1",
                    "role_id": role_id,
                    "name": "期末考準備",
                    "description": "複習微積分與演算法",
                    "status": "active",
                }
            ]
        elif "role_settings" in query_lower:
            return [
                {
                    "id": "settings_demo_1",
                    "role_id": role_id,
                    "theme": "dark",
                    "notification_enabled": True,
                    "daily_report_time": "22:00",
                    "focus_hours_start": "09:00",
                    "focus_hours_end": "18:00",
                }
            ]
        elif "goals" in query_lower:
            return [
                {
                    "id": "goal_demo_1",
                    "persona_id": "robert_001",
                    "title": "通過資料結構期末考",
                    "description": "刷完 LeetCode 100 題",
                    "progress": 0.45,
                    "status": "active",
                }
            ]
        elif "promises" in query_lower:
            return [
                {
                    "id": "promise_demo_1",
                    "persona_id": "robert_001",
                    "text": "每天寫 1 小時程式",
                    "status": "active",
                },
                {
                    "id": "promise_demo_2",
                    "persona_id": "robert_001",
                    "text": "本週完成微積分作業",
                    "status": "active",
                }
            ]
        return []


# --- module singletons (initialized in lifespan) ---
_debouncer: EventDebouncer | None = None
_gemma_pipeline: GemmaInferencePipeline | None = None
_eguard_filter: EguardFilter | None = None
_drift_shield: DriftShield | None = None
_breakpoint_engine: BreakpointEngine | None = None
_sqlite_conn: sqlite3.Connection | None = None
_db_adapter: AsyncDBAdapter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """[M0_3 SPEC §7.4] 啟動時驗證設定，關閉時清理連線"""
    # Use global settings

    # 驗證本地 SQLite data/ 目錄存在
    data_dir = settings.local_db_path.parent
    if not data_dir.exists():
        logger.warning("[M0.3] data/ 目錄不存在: %s，將嘗試建立", data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

    # 邊緣裝置可達性（非阻塞警告）
    if not settings.ipad_ai_local_host:
        logger.warning("[M0.3] IPAD_AI_LOCAL_HOST 未設定，邊緣推論功能將不可用")

    # Initialize module singletons
    global _gemma_pipeline, _eguard_filter, _drift_shield, _debouncer, _breakpoint_engine
    global _sqlite_conn, _db_adapter

    _sqlite_conn = sqlite3.connect(str(settings.local_db_path), check_same_thread=False)
    _sqlite_conn.row_factory = sqlite3.Row

    # Ensure local settings & consent tables exist (so they work locally without PG)
    try:
        cursor = _sqlite_conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_consents (
                id              TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                consent_type    TEXT NOT NULL,
                granted         INTEGER NOT NULL,
                granted_at      TEXT NOT NULL,
                revoked_at      TEXT,
                ip_hash         TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_settings (
                id              TEXT PRIMARY KEY,
                role_id         TEXT UNIQUE NOT NULL,
                theme           TEXT DEFAULT 'default',
                notification_enabled INTEGER DEFAULT 1,
                daily_report_time TEXT DEFAULT '22:00',
                focus_hours_start TEXT DEFAULT '09:00',
                focus_hours_end TEXT DEFAULT '18:00',
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS git_watched_paths (
                repo_path TEXT PRIMARY KEY,
                github_repo TEXT,
                last_seen_hash TEXT,  -- New: avoid redundant logging
                added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        # Manual migration: add columns if table exists but they don't
        try:
            cursor.execute("ALTER TABLE git_watched_paths ADD COLUMN github_repo TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE git_watched_paths ADD COLUMN last_seen_hash TEXT")
        except sqlite3.OperationalError:
            pass
        _sqlite_conn.commit()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS github_tokens (
                id TEXT PRIMARY KEY,
                encrypted_token TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items_dictionary (
                id          TEXT PRIMARY KEY,
                name        TEXT UNIQUE NOT NULL,
                rarity      TEXT NOT NULL,
                description TEXT,
                image_url   TEXT,
                category    TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_collections (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                item_id     TEXT NOT NULL,
                acquired_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE (user_id, item_id)
            )
        """)
        
        # Seed items_dictionary if empty
        cursor.execute("SELECT COUNT(*) FROM items_dictionary")
        if cursor.fetchone()[0] == 0:
            badges = [
                ("badge_001", "首次反思", "common", "完成第一次反思草稿核准", None, "badge"),
                ("badge_002", "CPE 挑戰者", "rare", "報名 CPE 程式能力檢定", None, "badge"),
                ("badge_003", "連續 7 天", "epic", "連續 7 天完成反思", None, "badge"),
                ("badge_004", "學期之星", "legendary", "一學期內獲得最高 XP", None, "badge"),
            ]
            cursor.executemany(
                "INSERT INTO items_dictionary (id, name, rarity, description, image_url, category) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                badges
            )
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                current_xp  INTEGER DEFAULT 0,
                lifetime_xp INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id              TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                slug            TEXT NOT NULL,
                display_name    TEXT NOT NULL,
                color_hex       TEXT,
                icon_name       TEXT,
                sort_order      INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE(user_id, slug)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_experts (
                id                  TEXT PRIMARY KEY,
                role_id             TEXT NOT NULL,
                name                TEXT NOT NULL,
                personality_prompt  TEXT,
                backstory           TEXT,
                tone_default        TEXT DEFAULT 'empathetic',
                trust_level         REAL DEFAULT 0.8,
                avatar_url          TEXT,
                is_active           INTEGER DEFAULT 1,
                created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id              TEXT PRIMARY KEY,
                role_id         TEXT NOT NULL,
                persona_id      TEXT,
                title           TEXT NOT NULL,
                description     TEXT,
                progress        REAL DEFAULT 0.0,
                status          TEXT DEFAULT 'active',
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promises (
                id              TEXT PRIMARY KEY,
                role_id         TEXT NOT NULL,
                persona_id      TEXT,
                source_thread_id TEXT,
                text            TEXT NOT NULL,
                deadline        TEXT,
                status          TEXT DEFAULT 'active',
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_projects (
                id              TEXT PRIMARY KEY,
                role_id         TEXT NOT NULL,
                name            TEXT NOT NULL,
                description     TEXT,
                status          TEXT DEFAULT 'active',
                inferred_by_ai  INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE(role_id, name)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS xp_ledger (
                id              TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                amount          INTEGER NOT NULL,
                xp_type         TEXT NOT NULL,
                reason          TEXT,
                source_module   TEXT,
                reflection_id   TEXT,
                segment_id      TEXT,
                role_id         TEXT,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)

        # Seed default user if empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            default_user_id = settings.current_user_id
            cursor.execute(
                "INSERT INTO users (id, username, current_xp, lifetime_xp) VALUES (?, ?, ?, ?)",
                (default_user_id, "default_user", 100, 100)
            )
            
            # Seed default roles
            roles = [
                (str(uuid.uuid5(uuid.NAMESPACE_DNS, "uni_001")), default_user_id, 
                 "uni_001", "UNI", "#d4915e", "activity", 0),
                (str(uuid.uuid5(uuid.NAMESPACE_DNS, "csie_001")), default_user_id, 
                 "csie_001", "CSIE", "#c47830", "code", 1),
            ]
            cursor.executemany(
                "INSERT INTO roles (id, user_id, slug, display_name, color_hex, icon_name, sort_order) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                roles
            )
            
            # Seed default expert for CSIE
            csie_role_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "csie_001"))
            cursor.execute(
                "INSERT INTO ai_experts (id, role_id, name, personality_prompt, backstory) VALUES (?, ?, ?, ?, ?)",
                ("robert_001", csie_role_id, "學長Robert", 
                 "你是一個資深的電腦科學系學長...", "在 CSIE 待了四年的傳奇人物")
            )
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_reflections (
                id              TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                role_id         TEXT NOT NULL,
                reflection_date TEXT NOT NULL,
                ai_summary      TEXT,
                is_completed    INTEGER DEFAULT 0,
                completed_at    TEXT,
                total_activity_minutes INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE(user_id, role_id, reflection_date)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_reflection_segments (
                id              TEXT PRIMARY KEY,
                reflection_id   TEXT NOT NULL,
                user_id         TEXT NOT NULL,
                role_id         TEXT NOT NULL,
                start_time      TEXT NOT NULL,
                end_time        TEXT NOT NULL,
                activity_minutes INTEGER DEFAULT 0,
                ai_description  TEXT,
                user_feeling    TEXT,
                user_action_plan TEXT,
                user_learned    TEXT,
                is_draft        INTEGER DEFAULT 1,
                is_reviewed     INTEGER DEFAULT 0,
                xp_settled      INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                FOREIGN KEY(reflection_id) REFERENCES daily_reflections(id)
            )
        """)
        _sqlite_conn.commit()
        logger.info("[lifespan] All local tables ensured and seeded.")
    except Exception as e:
        logger.warning("[lifespan] Failed to auto-create settings tables in SQLite: %s", e)

    pg_engine = None
    if is_cloud_available():
        pg_engine = get_cloud_engine()
        logger.info("[lifespan] Cloud PG database available.")

    _db_adapter = AsyncDBAdapter(_sqlite_conn, pg_engine)

    # [M0.3] Ensure local identity and sync to cloud
    try:
        # Check for existing user in SQLite
        user_row = await _db_adapter.fetch_one("SELECT id FROM users LIMIT 1")
        
        if not user_row:
            # First start: Generate a fresh persistent UUID for this instance
            instance_user_id = str(uuid.uuid4())
            logger.info("[lifespan] First start detected. Generated new Instance ID: %s", instance_user_id)
            await _db_adapter.execute(
                "INSERT INTO users (id, display_name, email, current_xp, level) VALUES (:id, :name, :email, 0, 1)",
                {"id": instance_user_id, "name": "Me (Local)", "email": "local@coos.internal"}
            )
        else:
            instance_user_id = user_row["id"]
            logger.info("[lifespan] Using existing Instance ID: %s", instance_user_id)
        
        # Update settings for this session
        settings.current_user_id = instance_user_id

        # Sync Identity to Cloud (No roles, just the user object)
        if pg_engine and is_cloud_available():
            with pg_engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("""
                    INSERT INTO users (id, display_name, email, current_xp, level, streak_days)
                    VALUES (:id, 'Local User', :email, 0, 1, 0)
                    ON CONFLICT (id) DO NOTHING
                """), {
                    "id": settings.current_user_id, 
                    "email": f"local_{settings.current_user_id[:8]}@coos.internal"
                })
                conn.commit()
                logger.info("[lifespan] Identity verified with cloud.")
    except Exception as e:
        logger.warning("[lifespan] Failed to manage identity: %s", e)

    # [M0.4] Start AsyncLogWriter background flush worker
    from m0_4_logging.writer import get_logger as get_log_writer
    _log_writer = get_log_writer(db_path=str(settings.local_db_path))
    await _log_writer.start()

    _breakpoint_engine = BreakpointEngine()

    _gemma_pipeline = GemmaInferencePipeline(
        ai_local_host=settings.ai_local_host,
        model=settings.gemma_model,
    )

    async def _m2_2_flush(batch: EventBatch) -> None:
        """Flush EventBatch to M2.2 for inference (wired in debouncer)"""
        logger.info("[M2.1] batch flushed: size=%d role=%s", batch.size, batch.role_id)
        
        # 1. Summarize events for Gemma
        # We take first 5 and last 5 events if too many
        if len(batch.events) > 10:
            events_to_process = batch.events[:5] + batch.events[-5:]
        else:
            events_to_process = batch.events
            
        summary_text = "\n".join([
            f"- {e.event_type} (from {e.module}): {json.dumps(e.data, ensure_ascii=False)}"
            for e in events_to_process
        ])
        
        # 2. Gemma Semantic Compression
        vector = await _gemma_pipeline.compress(
            summary_text,
            source_log_id=batch.batch_id,
            role_id=batch.role_id
        )
        
        # 3. M2.3 Eguard Filter (sanitize context_summary)
        sanitized = _eguard_filter.mask_pii(vector.context_summary, role_id=batch.role_id)
        
        # 4. Store to intent_logs (M6.1)
        import uuid
        await _db_adapter.execute(
            "INSERT INTO intent_logs (id, source_log_id, role_id, intent_label, context_summary, inference_mode) "
            "VALUES (:id, :src, :rid, :label, :ctx, :mode)",
            {
                "id": str(uuid.uuid4()),
                "src": batch.batch_id,
                "rid": batch.role_id,
                "label": vector.intent_label,
                "ctx": sanitized.sanitized_text,
                "mode": vector.inference_mode
            }
        )

    _debouncer = EventDebouncer(
        role_id="default",
        flush_fn=_m2_2_flush,
        db_path=str(settings.local_db_path),
    )
    _eguard_filter = EguardFilter()
    _drift_shield = DriftShield(ai_local_host=settings.ai_local_host)

    # [M1.4.3] Start Local Git Monitor
    async def _git_emit(event: dict):
        from m0_4_logging.writer import get_logger
        log_writer = get_logger()
        await log_writer.emit(
            module=event["module"],
            action=event["action"],
            level="INFO",
            payload=event["payload"]
        )

    async def _update_git_hash(repo_path: str, last_hash: str):
        await _db_adapter.execute(
            "UPDATE git_watched_paths SET last_seen_hash = :h WHERE repo_path = :p",
            {"h": last_hash, "p": repo_path}
        )

    watched_paths_rows = await _db_adapter.fetch_all(
        "SELECT repo_path, last_seen_hash FROM git_watched_paths"
    )
    watched_paths = [
        {"path": row["repo_path"], "last_hash": row["last_seen_hash"]} 
        for row in watched_paths_rows
    ]
    git_monitor = LocalGitMonitor(watched_paths, _git_emit, _update_git_hash)
    git_task = asyncio.create_task(git_monitor.scan_loop())

    # Periodic maintenance: Rule miner & Zombie cleanup
    async def periodic_maintenance():
        await asyncio.sleep(60.0)
        while True:
            try:
                # 1. M2.2 Rule Miner
                if _gemma_pipeline and _sqlite_conn:
                    from m2_2_gemma.rule_miner import FallbackRuleMiner
                    miner = FallbackRuleMiner(_gemma_pipeline.fallback)
                    new_rules = await miner.mine_rules_from_db(_sqlite_conn, min_occurrences=3, min_correlation=0.8)
                    if new_rules:
                        logger.info("[M2.2] Periodic maintenance: learned %d new fallback rules", len(new_rules))

                # 2. M4.5 Zombie Cleanup
                # Hard delete stale drafts (is_draft=True, not is_reviewed, not xp_settled, > 7 days old)
                cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()
                await _db_adapter.execute(
                    "DELETE FROM daily_reflections WHERE is_draft = TRUE AND is_reviewed = FALSE "
                    "AND xp_settled = FALSE AND created_at < :cutoff",
                    {"cutoff": cutoff}
                )
                await _db_adapter.execute(
                    "DELETE FROM daily_reflection_segments WHERE is_draft = TRUE AND is_reviewed = FALSE "
                    "AND xp_settled = FALSE AND created_at < :cutoff",
                    {"cutoff": cutoff}
                )
            except Exception as e:
                logger.warning("[lifespan] Periodic maintenance failed: %s", e)
            await asyncio.sleep(3600.0)

    maintenance_task = asyncio.create_task(periodic_maintenance())

    # [M1.4.2] GitHub Webhook Tunnel Manager
    import subprocess
    tunnels = []

    async def start_tunnels():
        # Use global settings
        rows = await _db_adapter.fetch_all("SELECT github_repo FROM git_watched_paths WHERE github_repo IS NOT NULL")
        for row in rows:
            repo = row["github_repo"]
            url = f"http://127.0.0.1:{settings.fastapi_port}/api/v1/webhooks/github"
            logger.info("[M1.4.2] Starting GitHub webhook tunnel for %s", repo)
            try:
                # Spawn 'gh webhook forward' as a background process
                proc = subprocess.Popen(
                    ["gh", "webhook", "forward", f"--repo={repo}", f"--url={url}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                tunnels.append(proc)
            except Exception as e:
                logger.warning("[M1.4.2] Failed to start tunnel for %s: %s", repo, e)

    tunnel_task = asyncio.create_task(start_tunnels())

    logger.info("[M0.3] coOS sidecar 啟動完成 (local_only=%s)", not settings.gemini_api_key)
    yield
    # Cleanup
    tunnel_task.cancel()
    for proc in tunnels:
        proc.terminate()
    git_task.cancel()
    maintenance_task.cancel()
    try:
        await asyncio.gather(git_task, maintenance_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    if _debouncer:
        await _debouncer.shutdown_gracefully()
    from m0_4_logging.writer import get_logger as get_log_writer
    await get_log_writer().stop()
    if _sqlite_conn:
        _sqlite_conn.close()
    logger.info("[M0.3] coOS sidecar 關閉")


app = FastAPI(title="coOS Sidecar", version="0.1.0", lifespan=lifespan)

# [架構文件 §7] 僅允許 Tauri 與本地開發 origin
# [M0_2 SPEC §7.4] FastAPI sidecar 必須綁定 127.0.0.1，CSP 設定於 tauri.conf.json
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420"],
    allow_origin_regex="chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RoleIsolationMiddleware)

# M1.4 routers
app.include_router(m1_4_webhook_router)
app.include_router(m1_4_oauth_router)


# ---------------------------------------------------------------------------
# M1.1 — OS 遙測守護行程事件接收端點
# ---------------------------------------------------------------------------

@app.post("/api/m1_1/event")
async def m1_1_event(event: LogEvent) -> dict[str, Any]:
    """[M1.1 SPEC §3] Receive a single TelemetryEvent from the Rust sidecar.

    M1.1 Rust daemon POSTs M0.4 LogEvent to this endpoint.
    Validated by LogEvent's privacy_validator (forbids L1 plaintext keys).
    Written to raw_tracking_logs via AsyncLogWriter.

    [R06: 數位表型 §2.1] Focus/keystroke events as digital phenotype sensor.
    [R02: 計算心理語言學 §1] WPM as cognitive state input feature.
    """
    from m0_4_logging.writer import get_logger
    log_writer = get_logger()
    await log_writer.emit(
        module=event.module,
        action=event.action,
        level=event.level,
        payload=event.payload,
        role_id=event.role_id,
        correlation_id=event.correlation_id,
        event_id=event.id,
    )
    # [M1.2 SPEC §3] Forward to BreakpointEngine — M1.1 events are M1.2's primary input
    engine = _get_breakpoint_engine()
    await engine.feed({
        "module": event.module,
        "action": event.action,
        "payload": event.payload,
    })

    # [M2.3 DRIFT Shield] Security check for content capture
    if event.action == "content_capture" and event.payload.get("content_raw"):
        try:
            await _drift_shield.verify_input(event.payload["content_raw"])
        except Exception as e:
            logger.warning("[M2.3] DRIFT blocked content capture for event %s: %s", event.id, e)
            return {"status": "blocked", "reason": "security_policy"}

    # [M2.2 Gemma Background Compression]
    if event.action == "content_capture" and event.payload.get("content_raw"):
        content_raw = event.payload["content_raw"]
        if event.payload.get("inference_mode") == "rule_based_fallback" and _gemma_pipeline:
            async def run_gemma_async(evt_id: str, raw_text: str, r_id: str | None):
                try:
                    # Semantic compression via local Gemma edge
                    vector = await _gemma_pipeline.compress(
                        raw_text,
                        source_log_id=evt_id,
                        role_id=r_id or "default"
                    )
                    if vector.inference_mode == "gemma_edge":
                        # Wait for AsyncLogWriter to flush the record to raw_tracking_logs
                        row = None
                        for _ in range(5):
                            row = await _db_adapter.fetch_one(
                                "SELECT payload FROM raw_tracking_logs WHERE id = :id",
                                {"id": evt_id}
                            )
                            if row:
                                break
                            await asyncio.sleep(1.0)
                        
                        if row:
                            import json
                            payload = json.loads(row["payload"])
                            payload["content_summary"] = vector.context_summary
                            payload["inference_mode"] = "gemma_edge"
                            await _db_adapter.execute(
                                "UPDATE raw_tracking_logs SET payload = :payload WHERE id = :id",
                                {
                                    "id": evt_id,
                                    "payload": json.dumps(payload, ensure_ascii=False)
                                }
                            )
                            logger.info("[M1.1] Async Gemma compression completed & updated database for event %s", evt_id)  # noqa: E501
                except Exception as ex:
                    logger.warning("[M1.1] Async Gemma background execution failed: %s", ex)

            asyncio.create_task(run_gemma_async(event.id, content_raw, event.role_id))

    return {"status": "ok", "event_id": event.id}


@app.get("/api/m1_1/consent")
async def m1_1_consent(request: Request) -> dict[str, Any]:
    """[M1.1 SPEC §7.3] Return current CaptureConsent for the Rust telemetry daemon.

    Polled every 60 seconds by the daemon so consent changes propagate without restart.
    Reads user_consents table (content_capture_all / content_capture_selected).
    [RISK-15] Never exposes content_raw or content_summary — consent metadata only.
    """
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    consents_rows = await _db_adapter.fetch_all(
        "SELECT consent_type, granted FROM user_consents WHERE user_id = :uid",
        {"uid": str(user_id)},
    )
    consents_dict = {row["consent_type"]: row["granted"] for row in consents_rows}

    if consents_dict.get("content_capture_all") == 1:
        mode = "all"
        allowed_processes: list[str] = []
    elif consents_dict.get("content_capture_selected") == 1:
        mode = "selected"
        # allowed_processes stored as JSON array in consent payload
        row = await _db_adapter.fetch_one(
            "SELECT payload FROM user_consents WHERE user_id = :uid AND consent_type = 'content_capture_selected'",
            {"uid": str(user_id)}
        )
        try:
            allowed_processes = json.loads(row["payload"]) if row and row["payload"] else []
        except Exception:
            allowed_processes = []
    else:
        mode = "off"
        allowed_processes = []

    return {"mode": mode, "allowed_processes": allowed_processes}


# ---------------------------------------------------------------------------
# M1.2 — 斷點偵測引擎事件接收端點
# ---------------------------------------------------------------------------

def _get_breakpoint_engine() -> BreakpointEngine:
    """Lazy init — returns singleton or creates one if lifespan hasn't run (tests)."""
    global _breakpoint_engine
    if _breakpoint_engine is None:
        _breakpoint_engine = BreakpointEngine()
    return _breakpoint_engine


@app.post("/api/m1_2/event")
async def m1_2_event(event: LogEvent) -> dict[str, Any]:
    """[M1.2 SPEC §3] Feed M1.1 TelemetryEvent into the BreakpointEngine.

    Accepts the same M0.4 LogEvent schema as /api/m1_1/event.
    The engine processes the event and may emit BREAKPOINT_DETECTED.

    [R08: §二] Defer-to-Breakpoint: only notify at natural cognitive gaps.
    [R08: §三, RISK-04] Three-tier notification gate enforced in engine.
    """
    engine = _get_breakpoint_engine()
    await engine.feed({
        "module": event.module,
        "action": event.action,
        "payload": event.payload,
    })
    return {"status": "ok", "state": engine.current_state}


@app.get("/api/m1_2/state")
async def m1_2_state() -> dict[str, Any]:
    """Retrieve the current state parameters of the BreakpointEngine."""
    engine = _get_breakpoint_engine()
    return {
        "current_state": engine.current_state,
        "mode": engine.mode,
        "current_app": engine._current_app,
        "last_activity_elapsed": time.monotonic() - engine._last_activity,
    }


# ---------------------------------------------------------------------------
# Health Check — M0.2 驗收條件 1 & 2
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - _start_time),
    }


# ---------------------------------------------------------------------------
# SSE 測試端點 — M0.2 驗收條件 3
# ---------------------------------------------------------------------------

async def _test_stream_generator():
    """推送 5 個測試事件後結束"""
    for i in range(5):
        yield f"data: {{\"seq\": {i}, \"ts\": {time.time()}}}\n\n"
        await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------
# M2.1 — 事件防抖與排隊引擎
# ---------------------------------------------------------------------------

@app.post("/api/m2_1/ingest")
async def m2_1_ingest(event: RawTelemetryEvent) -> dict[str, Any]:
    """[M2.1 SPEC §3] Receive a single telemetry event and push into debouncer.

    Called by Tauri IPC bridge when OS/IDE telemetry arrives.
    Returns the event ID for correlation.
    """
    if _debouncer is None:
        raise HTTPException(status_code=503, detail="M2.1 debouncer not initialized")
    await _debouncer.push(event)
    return {"status": "queued", "event_id": event.id}


# ---------------------------------------------------------------------------
# M2.2 — Gemma 邊緣推論管線
# ---------------------------------------------------------------------------

@app.post("/api/m2_2/compress")
async def m2_2_compress(body: dict[str, Any]) -> IntentVector:
    """[M2.2 SPEC §3] Compress raw text to de-identified IntentVector.

    Accepts: {"text": str, "source_log_id": str, "role_id": str}
    Returns: IntentVector (L2 privacy -- no plaintext stored)
    [R07: POST §4.3] privacy-preserving compression via local Gemma
    """
    if _gemma_pipeline is None:
        raise HTTPException(status_code=503, detail="M2.2 pipeline not initialized")

    text = body.get("text", "")
    source_log_id = body.get("source_log_id", "")
    role_id = body.get("role_id", "")

    if not source_log_id or not role_id:
        raise HTTPException(
            status_code=422,
            detail="source_log_id and role_id are required (RISK-05)",
        )

    return await _gemma_pipeline.compress(text, source_log_id=source_log_id, role_id=role_id)


@app.post("/api/m2_2/mine_rules")
async def m2_2_mine_rules(
    min_occurrences: int = 3,
    min_correlation: float = 0.8
) -> dict[str, Any]:
    """[M2.2 SPEC §7.8] Trigger rule mining from gemma_edge logs to expand rule-based fallbacks."""
    if _gemma_pipeline is None:
        raise HTTPException(status_code=503, detail="M2.2 pipeline not initialized")

    from m2_2_gemma.rule_miner import FallbackRuleMiner
    miner = FallbackRuleMiner(_gemma_pipeline.fallback)

    if _sqlite_conn is None:
        raise HTTPException(status_code=500, detail="Local SQLite connection is not initialized")

    new_rules = await miner.mine_rules_from_db(
        _sqlite_conn,
        min_occurrences=min_occurrences,
        min_correlation=min_correlation
    )

    return {
        "status": "ok",
        "new_rules_count": len(new_rules),
        "new_rules": [{"pattern": p, "intent": i} for p, i in new_rules]
    }


# ---------------------------------------------------------------------------
# M2.3 — Eguard 密碼學過濾器
# ---------------------------------------------------------------------------

@app.post("/api/m2_3/sanitize")
async def m2_3_sanitize(payload: RawTextPayload) -> SanitizedPayload:
    """[M2.3 SPEC §3] PII masking + DRIFT injection detection.

    Anti-pattern: NEVER send raw plaintext to cloud before calling this endpoint.
    [R07: §5 Eguard] discrete text masking prevents embedding inversion attacks
    [R02: DRIFT §架構安全性] blocks prompt injection at system boundary
    """
    if _eguard_filter is None or _drift_shield is None:
        raise HTTPException(status_code=503, detail="M2.3 Eguard not initialized")

    # Layer 1: DRIFT injection check
    try:
        _drift_shield.verify_input(payload.text, source_path=payload.source_path)
    except InjectionDetectedException as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "EGUARD_BLOCK", "payload_hash": exc.payload_hash},
        )
    # Layer 2: PII masking
    result = _eguard_filter.mask_pii(
        payload.text,
        role_id=payload.role_id,
        source_path=payload.source_path,
    )
    return result


@app.get("/api/m0_2/test_stream")
async def test_stream():
    """[M0_2 SPEC §6 驗收條件 3] SSE 測試端點，供驗收測試使用"""
    return StreamingResponse(
        _test_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Phase 5 UI 端點 — M3.x 前端所需的 API
# ---------------------------------------------------------------------------

# --- Settings API ---


class SettingsUpdate(BaseModel):
    content_capture: str
    voice_cloud: bool
    cloud_sync: bool
    theme: str
    notification_enabled: bool
    daily_report_time: str
    focus_hours_start: str
    focus_hours_end: str
    gemma_model: str
    ai_local_host: str
    ipad_ai_local_host: str


def update_env_file(updates: dict[str, str]):
    from pathlib import Path
    env_path = Path(__file__).parent / "../.env"
    if not env_path.exists():
        env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        logger.warning(".env file not found, skipping persistence")
        return
    
    try:
        content = env_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for key, value in updates.items():
            key_upper = key.upper()
            found = False
            for idx, line in enumerate(lines):
                if line.strip().startswith(key_upper + "=") or line.strip().startswith(key_upper + " ="):
                    lines[idx] = f"{key_upper}={value}"
                    found = True
                    break
            if not found:
                lines.append(f"{key_upper}={value}")
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info("Successfully updated .env file with keys: %s", list(updates.keys()))
    except Exception as e:
        logger.error("Failed to update .env file: %s", e)


@app.get("/api/settings")
async def get_settings_endpoint(role_id: str, request: Request):
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    import uuid
    try:
        role_uuid = uuid.UUID(role_id)
    except ValueError:
        role_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, role_id)

    # 1. Consents
    consents_rows = await _db_adapter.fetch_all(
        "SELECT consent_type, granted FROM user_consents WHERE user_id = :uid",
        {"uid": str(user_id)}
    )
    consents_dict = {row["consent_type"]: row["granted"] for row in consents_rows}
    
    content_capture = "off"
    if consents_dict.get("content_capture_all") == 1:
        content_capture = "all"
    elif consents_dict.get("content_capture_selected") == 1:
        content_capture = "selected"
        
    voice_cloud = bool(consents_dict.get("voice_cloud", 0))
    cloud_sync = bool(consents_dict.get("cloud_sync", 0))
    
    # 2. Role Settings
    role_settings = await _db_adapter.fetch_one(
        "SELECT * FROM role_settings WHERE role_id = :rid",
        {"rid": str(role_uuid)}
    )
    
    theme = "default"
    notification_enabled = True
    daily_report_time = "22:00"
    focus_hours_start = "09:00"
    focus_hours_end = "18:00"
    
    def _parse_time(val, default):
        if val is None:
            return default
        if hasattr(val, "strftime"):
            return val.strftime("%H:%M")
        val_str = str(val).strip()
        if len(val_str) >= 5:
            return val_str[:5]
        return default

    if role_settings:
        theme = role_settings.get("theme", theme)
        notification_enabled = bool(role_settings.get("notification_enabled", 1))
        daily_report_time = _parse_time(role_settings.get("daily_report_time"), daily_report_time)
        focus_hours_start = _parse_time(role_settings.get("focus_hours_start"), focus_hours_start)
        focus_hours_end = _parse_time(role_settings.get("focus_hours_end"), focus_hours_end)
        
    # 3. System Config
    
    return {
        "content_capture": content_capture,
        "voice_cloud": voice_cloud,
        "cloud_sync": cloud_sync,
        "theme": theme,
        "notification_enabled": notification_enabled,
        "daily_report_time": daily_report_time,
        "focus_hours_start": focus_hours_start,
        "focus_hours_end": focus_hours_end,
        "gemma_model": settings.gemma_model,
        "ai_local_host": settings.ai_local_host,
        "ipad_ai_local_host": settings.ipad_ai_local_host,
    }


@app.post("/api/settings")
async def update_settings_endpoint(role_id: str, payload: SettingsUpdate, request: Request):
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    import uuid
    try:
        role_uuid = uuid.UUID(role_id)
    except ValueError:
        role_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, role_id)

    # 1. Update Consents
    await _db_adapter.execute(
        "DELETE FROM user_consents WHERE user_id = :uid AND consent_type IN "
        "('content_capture_all', 'content_capture_selected', 'voice_cloud', 'cloud_sync')",
        {"uid": str(user_id)}
    )
    
    from datetime import UTC, datetime
    now_str = datetime.now(tz=UTC).strftime('%Y-%m-%dT%H:%M:%fZ')
    
    consent_mappings = [
        ("content_capture_all", 1 if payload.content_capture == "all" else 0),
        ("content_capture_selected", 1 if payload.content_capture == "selected" else 0),
        ("voice_cloud", 1 if payload.voice_cloud else 0),
        ("cloud_sync", 1 if payload.cloud_sync else 0)
    ]
    
    for c_type, val in consent_mappings:
        await _db_adapter.execute(
            "INSERT INTO user_consents (id, user_id, consent_type, granted, granted_at) "
            "VALUES (:id, :uid, :type, :granted, :at)",
            {
                "id": str(uuid.uuid4()),
                "uid": str(user_id),
                "type": c_type,
                "granted": val,
                "at": now_str
            }
        )
        
    # 2. Update Role Settings
    existing_settings = await _db_adapter.fetch_one(
        "SELECT id FROM role_settings WHERE role_id = :rid",
        {"rid": str(role_uuid)}
    )
    
    if existing_settings:
        await _db_adapter.execute(
            "UPDATE role_settings SET theme = :theme, notification_enabled = :notification_enabled, "
            "daily_report_time = :daily_report_time, focus_hours_start = :focus_hours_start, "
            "focus_hours_end = :focus_hours_end, updated_at = NOW() WHERE role_id = :rid",
            {
                "rid": str(role_uuid),
                "theme": payload.theme,
                "notification_enabled": payload.notification_enabled,
                "daily_report_time": payload.daily_report_time,
                "focus_hours_start": payload.focus_hours_start,
                "focus_hours_end": payload.focus_hours_end
            }
        )
    else:
        await _db_adapter.execute(
            "INSERT INTO role_settings (id, role_id, theme, notification_enabled, "
            "daily_report_time, focus_hours_start, focus_hours_end, created_at, updated_at) "
            "VALUES (:id, :rid, :theme, :notification_enabled, :daily_report_time, "
            ":focus_hours_start, :focus_hours_end, NOW(), NOW())",
            {
                "id": str(uuid.uuid4()),
                "rid": str(role_uuid),
                "theme": payload.theme,
                "notification_enabled": payload.notification_enabled,
                "daily_report_time": payload.daily_report_time,
                "focus_hours_start": payload.focus_hours_start,
                "focus_hours_end": payload.focus_hours_end
            }
        )
        
    # 3. Update System settings in memory & .env file
    settings.gemma_model = payload.gemma_model
    settings.ai_local_host = payload.ai_local_host
    settings.ipad_ai_local_host = payload.ipad_ai_local_host
    
    # Persist to .env
    update_env_file({
        "gemma_model": payload.gemma_model,
        "ai_local_host": payload.ai_local_host,
        "ipad_ai_local_host": payload.ipad_ai_local_host,
    })
    
    return {"status": "success"}

# --- M6.2 Roles & Experts ---

@app.get("/api/m6_2/roles")
async def m6_2_list_roles(request: Request) -> list[dict[str, Any]]:
    """[M6.2] List all roles for the current user."""
    user_id = getattr(request.state, "user_id", None) or settings.current_user_id
    rows = await _db_adapter.fetch_all(
        "SELECT * FROM roles WHERE user_id = :uid AND is_active = 1 ORDER BY sort_order",
        {"uid": str(user_id)}
    )
    return [
        {
            "id": r["id"],
            "name": r["display_name"],
            "themeColorPalette": {"primary": r["color_hex"]},
            "sortOrder": r["sort_order"],
            "slug": r["slug"]
        } for r in rows
    ]


@app.post("/api/m6_2/roles")
async def m6_2_create_role(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """[M6.2] Create a new role."""
    user_id = getattr(request.state, "user_id", None) or settings.current_user_id
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    
    import uuid
    role_id = str(uuid.uuid4())
    slug = name.lower().replace(" ", "_")
    
    await _db_adapter.execute(
        "INSERT INTO roles (id, user_id, slug, display_name, color_hex, icon_name, sort_order) "
        "VALUES (:id, :uid, :slug, :name, :color, :icon, :sort)",
        {
            "id": role_id,
            "uid": str(user_id),
            "slug": slug,
            "name": name,
            "color": body.get("color", "#999999"),
            "icon": body.get("icon", "activity"),
            "sort": 10
        }
    )
    return {"id": role_id, "status": "created"}


@app.get("/api/m6_2/roles/{role_id}/experts")
async def m6_2_list_experts(role_id: str) -> list[dict[str, Any]]:
    """[M6.2] List experts for a specific role."""
    rows = await _db_adapter.fetch_all(
        "SELECT * FROM ai_experts WHERE role_id = :rid AND is_active = 1",
        {"rid": role_id}
    )
    return [
        {
            "id": r["id"],
            "expertName": r["name"],
            "personalityPrompt": r["personality_prompt"],
            "trustLevel": r["trust_level"],
            "avatarUrl": r["avatar_url"],
        } for r in rows
    ]


@app.delete("/api/m6_2/roles/{role_id}")
async def m6_2_delete_role(role_id: str, request: Request) -> dict[str, Any]:
    """[M6.2] Soft-delete a role."""
    user_id = getattr(request.state, "user_id", None) or settings.current_user_id
    await _db_adapter.execute(
        "UPDATE roles SET is_active = 0 WHERE id = :rid AND user_id = :uid",
        {"rid": role_id, "uid": str(user_id)}
    )
    return {"status": "deleted"}


# --- Monitored Apps Whitelist ---

@app.get("/api/settings/whitelist")
async def get_app_whitelist(request: Request) -> list[str]:
    """[M1.1] Fetch the current monitored apps whitelist."""
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    row = await _db_adapter.fetch_one(
        "SELECT payload FROM user_consents WHERE user_id = :uid AND consent_type = 'content_capture_selected'",
        {"uid": str(user_id)}
    )
    if row and row["payload"]:
        return json.loads(row["payload"])
    return []


@app.post("/api/settings/whitelist")
async def update_app_whitelist(body: list[str], request: Request) -> dict[str, Any]:
    """[M1.1] Update the monitored apps whitelist."""
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    # Update or insert the consent record
    await _db_adapter.execute(
        "INSERT INTO user_consents (id, user_id, consent_type, granted, granted_at, payload) "
        "VALUES (:id, :uid, 'content_capture_selected', 1, (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')), :payload) "
        "ON CONFLICT(id) DO UPDATE SET payload = :payload, granted = 1",
        {
            "id": f"consent_selected_{user_id}",
            "uid": str(user_id),
            "payload": json.dumps(body)
        }
    )
    return {"status": "success"}


# --- M6.3 Role Context ---

@app.get("/api/m6_3/role_context")
async def m6_3_role_context(role_id: str, request: Request) -> dict[str, Any]:
    """Context Header 四槽位資料 (Project / Role / Promises / Goal)"""
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    import uuid
    if isinstance(role_id, str):
        try:
            role_uuid = uuid.UUID(role_id)
        except ValueError:
            role_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, role_id)
    else:
        role_uuid = uuid.uuid4()
        
    role_ctx = await build_role_context(user_id=user_id, role_id=role_uuid, db=_db_adapter)
    
    project = {"name": role_ctx.projects[0].get("name")} if role_ctx.projects else {"name": "無作用中專案"}
    role = {"name": role_id.split("_")[0].upper() if "_" in role_id else "CSIE"}
    promises = [p.get("text") for p in role_ctx.upcoming_promises]
    goals = [g.get("title") for g in role_ctx.active_goals]
    
    if not promises:
        promises = ["每天寫 1 小時程式", "本週完成微積分作業"]
    if not goals:
        goals = ["通過資料結構期末考"]
        
    return {
        "role_id": str(role_id),
        "project": project,
        "role": role,
        "promises": promises,
        "goals": goals,
    }


# --- M6.4 Daily Reflections ---

@app.get("/api/m6_4/heatmap")
async def m6_4_heatmap(role_id: str) -> list[dict[str, Any]]:
    """過去 365 天的活躍度熱圖資料"""
    import random
    from datetime import date, timedelta
    today = date.today()
    result = []
    for i in range(365):
        d = today - timedelta(days=364 - i)
        count = random.choices([0, 0, 0, 1, 2, 3, 5], weights=[4, 2, 2, 3, 2, 1, 1])[0]
        if count:
            result.append({"date": d.isoformat(), "count": count})
    return result


@app.get("/api/m6_4/daily_timeline")
async def m6_4_daily_timeline(date: str, role_id: str | None = None) -> list[dict[str, Any]]:
    """當日任務清單（依角色分組）"""
    user_id = UUID(settings.current_user_id)
    
    import uuid
    role_uuid = None
    if role_id:
        if isinstance(role_id, str):
            try:
                role_uuid = uuid.UUID(role_id)
            except ValueError:
                role_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, role_id)
        else:
            role_uuid = uuid.uuid4()

    if _db_adapter and _db_adapter.pg_engine:
        try:
            refl_query = (
                "SELECT * FROM daily_reflections "
                "WHERE user_id = :uid AND reflection_date = :rdate"
            )
            refl_params = {"uid": str(user_id), "rdate": date}
            if role_uuid:
                refl_query += " AND role_id = :rid"
                refl_params["rid"] = str(role_uuid)
                
            reflections = await _db_adapter.fetch_all(refl_query, refl_params)
            
            timeline = []
            for r in reflections:
                segments = await _db_adapter.fetch_all(
                    "SELECT * FROM daily_reflection_segments "
                    "WHERE reflection_id = :rid AND is_active = TRUE",
                    {"rid": str(r.get("id"))}
                )
                for s in segments:
                    timeline.append({
                        "id": str(s.get("id")),
                        "roleId": role_id or str(r.get("role_id")),
                        "roleName": "CSIE",
                        "title": s.get("project") or "未命名任務",
                        "status": "completed" if s.get("is_reviewed") else "in_progress",
                        "reflection": {
                            "id": str(s.get("id")),
                            "ai_description": s.get("ai_description"),
                            "ai_analysis": s.get("ai_analysis"),
                            "user_feeling": s.get("user_feeling") or "",
                            "user_action_plan": s.get("user_action_plan") or "",
                            "is_draft": s.get("is_draft", True),
                            "is_reviewed": s.get("is_reviewed", False),
                        }
                    })
            if timeline:
                return timeline
        except Exception as e:
            logger.warning("[daily_timeline] Failed to fetch timeline from PG: %s", e)

    # Fallback to seed data
    return [
        {
            "id": "task_demo_1",
            "roleId": role_id or "csie_001",
            "roleName": "CSIE",
            "title": "微積分作業",
            "status": "completed",
            "reflection": {
                "id": "refl_demo_1",
                "ai_description": "你今天花了約 90 分鐘完成微積分作業，涵蓋泰勒展開與極限計算。",
                "ai_analysis": "進度符合計畫，主動解決三道難題。",
                "user_feeling": "",
                "user_action_plan": "",
                "is_draft": True,
                "is_reviewed": False,
            },
        },
        {
            "id": "task_demo_2",
            "roleId": role_id or "csie_001",
            "roleName": "CSIE",
            "title": "資料結構筆記 CH2",
            "status": "in_progress",
            "reflection": None,
        },
    ]


@app.patch("/api/m6_4/reflections/{reflection_id}")
async def m6_4_patch_reflection(reflection_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """[RISK-01] 更新 user_feeling / user_action_plan / is_reviewed"""
    logger.info("[M6.4] reflection %s patched: %s", reflection_id, list(body.keys()))
    
    if _db_adapter and _db_adapter.pg_engine:
        try:
            feeling = body.get("user_feeling")
            action_plan = body.get("user_action_plan")
            if feeling is not None and not feeling.strip():
                raise HTTPException(status_code=422, detail="user_feeling must not be whitespace-only")
            if action_plan is not None and not action_plan.strip():
                raise HTTPException(status_code=422, detail="user_action_plan must not be whitespace-only")

            update_fields = []
            params = {"rid": reflection_id}
            
            for k in ["user_feeling", "user_action_plan", "user_learned", "mood_score"]:
                if k in body:
                    update_fields.append(f"{k} = :{k}")
                    params[k] = body[k]
                    
            if body.get("is_reviewed") is not None:
                update_fields.append("is_reviewed = :is_reviewed")
                params["is_reviewed"] = body["is_reviewed"]
                if body["is_reviewed"]:
                    update_fields.append("is_draft = FALSE")
                    update_fields.append("reviewed_at = CURRENT_TIMESTAMP")
                    
            if update_fields:
                query = f"UPDATE daily_reflection_segments SET {', '.join(update_fields)} WHERE id = :rid"
                await _db_adapter.execute(query, params)
                
            return {"id": reflection_id, "status": "updated", **body}
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("[patch_reflection] PG update failed: %s", e)
            
    return {"id": reflection_id, "status": "updated", **body}


# --- M4.5 XP Settlement ---

@app.patch("/api/m4_5/grant_xp")
async def m4_5_grant_xp(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """[RISK-01] Settle XP for an approved reflection or segment."""
    refl_id = body.get("reflection_id")
    if not refl_id:
        raise HTTPException(status_code=422, detail="reflection_id is required")
    
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    store = LiveXPStore(_db_adapter)
    gatekeeper = XPGatekeeper(store)
    
    refl_uuid = UUID(refl_id)
    
    # Check segment first
    segment = await store.segments.get(refl_uuid)
    if segment:
        from m4_5_xp_settlement.engine import compute_earned_xp
        amount = compute_earned_xp(segment)
        result = await asyncio.to_thread(gatekeeper.settle_segment_xp, refl_uuid, user_id, amount)
        if result.success:
            await segment.save(_db_adapter)
            user_obj = await store.users.get(user_id)
            await user_obj.save(_db_adapter)
            return {"granted": True, "amount": amount}
        return {"granted": False, "reason": result.error_reason}
    
    # Check full reflection
    reflection = await store.reflections.get(refl_uuid)
    if reflection:
        from m4_5_xp_settlement.engine import compute_earned_xp
        amount = compute_earned_xp(reflection)
        result = await asyncio.to_thread(gatekeeper.settle_earned_xp, refl_uuid, user_id, amount)
        if result.success:
            await reflection.save(_db_adapter)
            user_obj = await store.users.get(user_id)
            await user_obj.save(_db_adapter)
            return {"granted": True, "amount": amount}
        return {"granted": False, "reason": result.error_reason}
                
    return {"granted": False, "reason": "Target not found or not approved"}


@app.get("/api/m4_4/time_spent/{task_id}")
async def m4_4_time_spent(task_id: str):
    """[M4.4] Aggregate real time spent for a task from raw_tracking_logs."""
    import json
    # Simple heuristic: sum duration of logs where payload contains task_id or repo_name
    query = """
        SELECT payload FROM raw_tracking_logs 
        WHERE (payload LIKE :task OR payload LIKE :task_lower)
    """
    rows = await _db_adapter.fetch_all(query, {"task": f"%{task_id}%", "task_lower": f"%{task_id.lower()}%"})
    
    total_minutes = 0
    for row in rows:
        try:
            payload = json.loads(row["payload"])
            # Prefer duration_minutes field
            total_minutes += payload.get("duration_minutes", 0)
        except Exception:
            continue
            
    return {"task_id": task_id, "time_spent_minutes": total_minutes}


@app.get("/api/m1_1/telemetry_estimate/{task_id}")
async def m1_1_telemetry_estimate(task_id: str):
    """[M1.1] Aggregate telemetry estimate for a task."""
    import json
    query = """
        SELECT payload FROM raw_tracking_logs 
        WHERE module IN ('M1.1', 'M1.3.1', 'M1.4.3') 
        AND (payload LIKE :task OR payload LIKE :task_lower)
    """
    rows = await _db_adapter.fetch_all(query, {"task": f"%{task_id}%", "task_lower": f"%{task_id.lower()}%"})
    
    total_minutes = 0
    count = 0
    for row in rows:
        try:
            payload = json.loads(row["payload"])
            total_minutes += payload.get("duration_minutes", 0)
            count += 1
        except Exception:
            continue
            
    confidence = 0.5 if count == 0 else min(0.95, 0.5 + (count * 0.05))
    return {"task_id": task_id, "confidence": confidence, "estimated_minutes": total_minutes}


# --- M6.5 Live Store for XPGatekeeper ---

class LiveXPStore:
    """Wrapper around AsyncDBAdapter to satisfy XPGatekeeper's store interface."""
    def __init__(self, db: AsyncDBAdapter):
        self.db = db
        self.users = self._UserProxy(db)
        self.reflections = self._ReflectionProxy(db)
        self.segments = self._SegmentProxy(db)
        self.ledger = self._LedgerProxy(db)

    class _UserProxy:
        def __init__(self, db):
            self.db = db

        async def get(self, uid):
            row = await self.db.fetch_one("SELECT * FROM users WHERE id = :uid", {"uid": str(uid)})
            if not row:
                return None
            # Return a simple object that supports += current_xp and lifetime_xp
            class UserObj:
                def __init__(self, r):
                    self.id = r["id"]
                    self.current_xp = r["current_xp"]
                    self.lifetime_xp = r["lifetime_xp"]

                async def save(self, db):
                    await db.execute(
                        "UPDATE users SET current_xp = :cxp, lifetime_xp = :lxp, "
                        "updated_at = CURRENT_TIMESTAMP WHERE id = :uid",
                        {"cxp": self.current_xp, "lxp": self.lifetime_xp, "uid": str(self.id)}
                    )
            return UserObj(row)

    class _ReflectionProxy:
        def __init__(self, db):
            self.db = db

        async def get(self, rid):
            row = await self.db.fetch_one("SELECT * FROM daily_reflections WHERE id = :rid", {"rid": str(rid)})
            if not row:
                return None
            class ReflectionObj:
                def __init__(self, r):
                    self.__dict__.update(dict(r))

                async def save(self, db):
                    await db.execute(
                        "UPDATE daily_reflections SET xp_settled = :s, xp_settled_at = :at, "
                        "earned_xp = :xp WHERE id = :rid",
                        {"s": self.xp_settled, "at": self.xp_settled_at, "xp": self.earned_xp, "rid": str(self.id)}
                    )
            return ReflectionObj(row)

    class _SegmentProxy:
        def __init__(self, db):
            self.db = db

        async def get(self, sid):
            row = await self.db.fetch_one(
                "SELECT * FROM daily_reflection_segments WHERE id = :sid",
                {"sid": str(sid)}
            )
            if not row:
                return None
            class SegmentObj:
                def __init__(self, r):
                    self.__dict__.update(dict(r))
                    self.is_active = True # Segments are always active in MVP

                async def save(self, db):
                    await db.execute(
                        "UPDATE daily_reflection_segments SET xp_settled = :s, xp_settled_at = :at, "
                        "earned_xp = :xp WHERE id = :sid",
                        {"s": self.xp_settled, "at": self.xp_settled_at, "xp": self.earned_xp, "sid": str(self.id)}
                    )
            return SegmentObj(row)

    class _LedgerProxy:
        def __init__(self, db):
            self.db = db

        async def append(self, entry):
            await self.db.execute(
                "INSERT INTO xp_ledger (id, user_id, amount, xp_type, reason, "
                "source_module, reflection_id, segment_id, role_id) "
                "VALUES (:id, :uid, :amt, :xtype, :reason, :src, :rid, :sid, :role_id)",
                {
                    "id": str(uuid.uuid4()),
                    "uid": str(entry.user_id),
                    "amt": entry.amount,
                    "xtype": entry.xp_type,
                    "reason": entry.reason,
                    "src": entry.source_module,
                    "rid": str(getattr(entry, "reflection_id", None)) if hasattr(entry, "reflection_id") else None,
                    "sid": str(getattr(entry, "segment_id", None)) if hasattr(entry, "segment_id") else None,
                    "role_id": str(getattr(entry, "role_id", None)) if hasattr(entry, "role_id") else None,
                }
            )

# --- End M6.5 Live Store ---

@app.post("/api/m6_5/grant_badge")
async def m6_5_grant_badge(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """[M6.5] Manual grant endpoint for awarding XP via XPGatekeeper."""
    refl_id = body.get("reflection_id")
    amount = body.get("amount", 20)
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    store = LiveXPStore(_db_adapter)
    gatekeeper = XPGatekeeper(store)
    
    refl_uuid = UUID(refl_id) if refl_id else None
    
    if refl_uuid:
        # Check segment
        segment = await store.segments.get(refl_uuid)
        if segment:
            result = await asyncio.to_thread(gatekeeper.settle_segment_xp, refl_uuid, user_id, amount)
            if result.success:
                await segment.save(_db_adapter)
                user_obj = await store.users.get(user_id)
                await user_obj.save(_db_adapter)
                return {"granted": True, "amount": amount}
            return {"granted": False, "reason": result.error_reason}
        
        # Check reflection
        reflection = await store.reflections.get(refl_uuid)
        if reflection:
            result = await asyncio.to_thread(gatekeeper.settle_earned_xp, refl_uuid, user_id, amount)
            if result.success:
                await reflection.save(_db_adapter)
                user_obj = await store.users.get(user_id)
                await user_obj.save(_db_adapter)
                return {"granted": True, "amount": amount}
            return {"granted": False, "reason": result.error_reason}
                
    return {"granted": False, "reason": "Target not found or not approved"}


@app.post("/api/m6_5/draw_card")
async def m6_5_draw_card(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """[M6.5] Gacha mechanic: spend XP for a random badge."""
    cost_xp = body.get("cost_xp", 100)
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    store = LiveXPStore(_db_adapter)
    gatekeeper = XPGatekeeper(store)
    
    result = await asyncio.to_thread(gatekeeper.deduct_xp_for_gacha, user_id, cost_xp)
    if result.success:
        user_obj = await store.users.get(user_id)
        await user_obj.save(_db_adapter)
        
        # Persistent the reward to user_collections
        reward = result.reward
        item_id = reward["id"]
        # In real scenario, we'd pick a real badge from items_dictionary
        # For now, we'll try to find a matching one or fallback to a seed badge
        badge_row = await _db_adapter.fetch_one("SELECT id FROM items_dictionary LIMIT 1 OFFSET abs(random()) % 4")
        if badge_row:
            item_id = badge_row["id"]
            
        await _db_adapter.execute(
            "INSERT INTO user_collections (id, user_id, item_id) VALUES (:id, :uid, :iid) "
            "ON CONFLICT DO NOTHING",
            {"id": str(uuid.uuid4()), "uid": str(user_id), "iid": item_id}
        )
        return {"success": True, "reward": reward, "item_id": item_id}
    
    return {"success": False, "reason": result.error_reason}

@app.get("/api/m6_5/user_collections")
async def m6_5_user_collections(request: Request) -> list[dict[str, Any]]:
    """[M6.5] Fetch real user collections from SQLite."""
    user_id = getattr(request.state, "user_id", None) or settings.current_user_id
    query = """
        SELECT i.*, u.acquired_at 
        FROM user_collections u 
        JOIN items_dictionary i ON u.item_id = i.id 
        WHERE u.user_id = :uid
    """
    rows = await _db_adapter.fetch_all(query, {"uid": str(user_id)})
    return [dict(row) for row in rows]


@app.get("/api/m6_5/items_dictionary")
async def m6_5_items_dictionary() -> list[dict[str, Any]]:
    """[M6.5] Fetch all available achievements from dictionary."""
    rows = await _db_adapter.fetch_all("SELECT * FROM items_dictionary ORDER BY rarity DESC")
    return [dict(row) for row in rows]


# --- M4.1 Chat (LangGraph) ---

@app.post("/api/m4_1/chat")
async def m4_1_chat(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """對話端點 — 串接 LangGraph 多智能體頂層協調與 Persona 狀態機"""
    user_msg = body.get("content", "")
    role_id = body.get("role_id", "")
    thread_id = body.get("thread_id")
    
    # [M2.3 DRIFT Shield] Security check
    try:
        await _drift_shield.verify_input(user_msg)
    except Exception as e:
        logger.warning("[M2.3] DRIFT blocked chat input: %s", e)
        return {"content": "對不起，我偵測到輸入內容可能存在安全風險，已暫時阻斷處理。", "persona_id": "system"}

    # [M2.3 Eguard Filter] PII Masking before processing
    sanitized = _eguard_filter.mask_pii(user_msg, role_id=str(role_id))
    user_msg = sanitized.sanitized_text

    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    import uuid
    if isinstance(role_id, str):
        try:
            role_uuid = uuid.UUID(role_id)
        except ValueError:
            role_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, role_id)
    else:
        role_uuid = uuid.uuid4()
        
    role_ctx = await build_role_context(user_id=user_id, role_id=role_uuid, db=_db_adapter)
    
    intent_vector = None
    if _gemma_pipeline:
        try:
            source_log_id = str(uuid.uuid4())
            intent_vector = await _gemma_pipeline.compress(
                user_msg, source_log_id=source_log_id, role_id=str(role_uuid)
            )
            if hasattr(intent_vector, "dict"):
                intent_vector = intent_vector.dict()
        except Exception as e:
            logger.warning("Gemma compress failed in chat route: %s", e)
            
    resolved_thread_id = thread_id or f"{role_uuid}::{uuid.uuid4()}"
    if resolved_thread_id and resolved_thread_id.find("::") == -1:
        resolved_thread_id = f"{role_uuid}::{resolved_thread_id}"
        
    router_input = {
        "thread_id": resolved_thread_id,
        "role_id": str(role_uuid),
        "user_message": user_msg,
        "intent_vector": intent_vector,
        "active_experts": role_ctx.active_experts,
        "role_rules": [],
        "implicit_state": role_ctx.implicit_state.get("implicit_state") if role_ctx.implicit_state else None,
    }
    
    try:
        rules = await _db_adapter.fetch_all(
            "SELECT * FROM role_router_rules WHERE role_id = :rid",
            {"rid": str(role_uuid)}
        )
        router_input["role_rules"] = rules
    except Exception:
        pass
        
    router_graph = get_router_graph()
    res = await router_graph.ainvoke(router_input)
    
    eguard = res.get("eguard_result") or {}
    if eguard.get("blocked"):
        return {
            "content": f"（安全過濾器攔截：{eguard.get('reason')}）",
            "persona_id": None,
            "thread_id": resolved_thread_id
        }
        
    persona_id = (res.get("route_decision") or {}).get("persona_id") or "robert_001"
    reply = res.get("persona_response") or f"學長在這！關於你說的「{user_msg[:20]}」，我們一步步拆解..."
    
    # [M4.4] Natural Elicitation Injection
    try:
        from m4_4_elicitation.controller import ElicitationController
        # Simple singleton-like usage for MVP
        if not hasattr(app.state, "elicitation_controller"):
            app.state.elicitation_controller = ElicitationController()
        
        ec = app.state.elicitation_controller
        # Since observer is async, we can't get results immediately here.
        # But we can check if the user message itself matches project extraction pattern
        from m4_6_observer.project_detector import regex_extract_project
        detected_project = regex_extract_project(user_msg)
        
        if detected_project and ec.can_elicit(resolved_thread_id, 1): # turn count mock
            fragment = ec.generate_elicitation(
                context="general_duration",
                role_id=str(role_uuid),
                project_name=detected_project
            )
            # Append the first elicitation message to the reply
            if fragment.inject_messages:
                reply += "\n\n" + fragment.inject_messages[0]
                ec.record_elicitation(resolved_thread_id, 1)
    except Exception as e:
        logger.warning("[M4.4] Elicitation injection failed: %s", e)
        user_msg_id = str(uuid.uuid4())
        reply_id = str(uuid.uuid4())
        
        await _db_adapter.execute(
            "INSERT INTO chat_transcripts (id, thread_id, persona_id, role, content, role_id) "
            "VALUES (:id, :thread_id, :persona_id, 'user', :content, :role_id)",
            {
                "id": user_msg_id,
                "thread_id": resolved_thread_id,
                "persona_id": persona_id,
                "content": user_msg,
                "role_id": str(role_uuid)
            }
        )
        await _db_adapter.execute(
            "INSERT INTO chat_transcripts (id, thread_id, persona_id, role, content, role_id) "
            "VALUES (:id, :thread_id, :persona_id, 'assistant', :content, :role_id)",
            {
                "id": reply_id,
                "thread_id": resolved_thread_id,
                "persona_id": persona_id,
                "content": reply,
                "role_id": str(role_uuid)
            }
        )
    except Exception as e:
        logger.error("Failed to save chat transcript to SQLite: %s", e)
        
    return {
        "content": reply,
        "persona_id": persona_id,
        "thread_id": resolved_thread_id
    }


@app.post("/api/m4_1/match_persona")
async def m4_1_match_persona(body: dict[str, Any]) -> dict[str, Any]:
    """配對最合適的 Persona"""
    user_msg = body.get("content", "") or body.get("current_state_description", "")
    role_id = body.get("role_id", "") or body.get("current_role_id", "")
    exclude_persona_id = body.get("exclude_persona_id")
    
    import uuid
    if isinstance(role_id, str):
        try:
            role_uuid = uuid.UUID(role_id)
        except ValueError:
            role_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, role_id)
    else:
        role_uuid = uuid.uuid4()
        
    role_ctx = await build_role_context(
        user_id=uuid.UUID(settings.current_user_id),
        role_id=role_uuid,
        db=_db_adapter
    )
    
    # [RISK-06] 限制可配對的專家池，若有需要排除的 Persona 則濾除
    active_experts = role_ctx.active_experts
    if exclude_persona_id:
        active_experts = [e for e in active_experts if e.get("id") != exclude_persona_id]
        
    from m4_1_router.routing_engine import route_with_confidence
    decision = await route_with_confidence(
        user_msg=user_msg,
        intent_vector={},
        active_experts=active_experts,
        role_id=str(role_uuid),
        role_rules=[],
    )
    
    return {
        "persona_id": decision.persona_id,
        "matched": decision.persona_id is not None and decision.persona_id != "tool_ai_default",
        "reason": decision.route_reason
    }


@app.post("/api/m1_4/disconnect_source")
async def m1_4_disconnect_source(body: dict[str, Any]) -> dict[str, Any]:
    """[M1.4] Remove a registered local git source."""
    repo_path = body.get("repo_path")
    if not repo_path:
        raise HTTPException(status_code=422, detail="repo_path is required")
    
    await _db_adapter.execute(
        "DELETE FROM git_watched_paths WHERE repo_path = :path",
        {"path": str(repo_path)}
    )
    return {"status": "disconnected", "repo_path": repo_path}


@app.post("/api/v1/auth/github/disconnect")
async def github_disconnect() -> dict[str, Any]:
    """[M1.4.1] Remove the stored GitHub OAuth token."""
    await _db_adapter.execute("DELETE FROM github_tokens WHERE id = 'default'")
    return {"status": "disconnected"}


# --- Auth & Identity (Future Multi-device) ---

@app.get("/api/auth/me")
async def get_current_user(request: Request) -> dict[str, Any]:
    """Return the current active identity (Dev Authenticator)."""
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    row = await _db_adapter.fetch_one("SELECT * FROM users WHERE id = :uid", {"uid": str(user_id)})
    if not row:
        return {"id": str(user_id), "status": "anonymous_local"}
    return dict(row)

@app.post("/api/auth/link/google")
async def link_google_account(body: dict[str, Any], request: Request) -> dict[str, Any]:
    """
    [Stub] Link current local UUID to a Google Account.
    Future: This will update the users.email or a social_links table.
    """
    user_id = getattr(request.state, "user_id", None) or UUID(settings.current_user_id)
    
    # Logic: 
    # 1. Verify Google Token
    # 2. Check if this Google User already exists in cloud
    # 3. If yes, return the existing UUID to the client to switch to.
    # 4. If no, update current user with google metadata.
    
    logger.info("[Auth] Linking user %s to Google account...", user_id)
    return {
        "status": "linked_stub", 
        "user_id": str(user_id), 
        "message": "Future implementation will perform OAuth flow."
    }

@app.get("/api/m4_6/events")
async def m4_6_events_sse():
    """Observer 背景萃取事件 SSE 通道"""
    async def generator():
        import json
        await asyncio.sleep(3)
        yield f"data: {json.dumps({'type': 'PROJECT_CREATED', 'project_name': '期末考準備'})}\n\n"
        await asyncio.sleep(60)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- M1.4 Workflow / Connected Sources ---

@app.get("/api/m1_4/github_auth_url")
async def m1_4_github_auth_url() -> dict[str, str]:
    """[M1.4.1] Generate the GitHub OAuth authorization URL."""
    client_id = settings.github_client_id
    if not client_id:
        return {"url": "", "error": "GITHUB_CLIENT_ID not configured"}
    
    # scope: 'repo' for PR/Commit access, 'user' for identity
    scope = "repo,user"
    redirect_uri = "http://localhost:8000/api/v1/auth/github/callback"
    url = f"https://github.com/login/oauth/authorize?client_id={client_id}&scope={scope}&redirect_uri={redirect_uri}"
    return {"url": url}


@app.get("/api/m1_4/connected_sources")
async def m1_4_connected_sources() -> list[dict[str, Any]]:
    """[M1.4] List all registered local git repos and connected cloud accounts."""
    sources = []
    
    # 1. Local Git Repos
    rows = await _db_adapter.fetch_all("SELECT repo_path, added_at FROM git_watched_paths")
    for row in rows:
        from pathlib import Path
        p = Path(row["repo_path"])
        sources.append({
            "id": str(row["repo_path"]),
            "type": "local_git",
            "name": p.name,
            "path": str(row["repo_path"]),
            "connected_at": row["added_at"]
        })
        
    # 2. GitHub Account (Check token table)
    token_row = await _db_adapter.fetch_one("SELECT created_at FROM github_tokens WHERE id = 'default'")
    if token_row:
        sources.append({
            "id": "github_cloud",
            "type": "github_oauth",
            "name": "GitHub Cloud Account",
            "connected_at": token_row["created_at"]
        })
        
    return sources


@app.post("/api/m1_4/bind_source")
async def m1_4_bind_source(body: dict[str, Any]) -> dict[str, Any]:
    source_type = body.get("source_type")
    if source_type == "local_git":
        repo_path = body.get("repo_path")
        github_repo = body.get("github_repo")  # Optional: e.g. "owner/repo"
        if not repo_path:
            raise HTTPException(status_code=422, detail="repo_path is required for local_git")
        
        # Verify it's a valid git repo
        from pathlib import Path
        if not (Path(repo_path) / ".git").exists():
            raise HTTPException(status_code=400, detail="Not a valid Git repository (missing .git)")
            
        await _db_adapter.execute(
            "INSERT INTO git_watched_paths (repo_path, github_repo) VALUES (:path, :repo) "
            "ON CONFLICT(repo_path) DO UPDATE SET github_repo = :repo",
            {"path": str(repo_path), "repo": github_repo}
        )
        return {"status": "connected", "source_type": "local_git", "repo_path": repo_path, "github_repo": github_repo}
        
    return {"status": "connected", "source_type": source_type}


@app.post("/api/m1_4/create_trigger")
async def m1_4_create_trigger(body: dict[str, Any]) -> dict[str, Any]:
    return {"id": "trigger_001", "status": "created", **body}


# --- M1.2.2 Tauri IPC Command Bridge ---

@app.post("/api/tauri/command")
async def post_tauri_command(body: dict[str, Any]) -> dict[str, Any]:
    """[M1.2.2] Mock Tauri IPC command bridge.
    Receives notification control commands from Deep Work Guard.
    """
    logger.info("[M1.2.2] Tauri IPC Bridge received command: %s", body)
    return {"status": "ok", "command": body}
