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


def get_safe_user_id(request: Request) -> UUID:
    """Helper to safely get user_id from request state or settings."""
    uid_str = getattr(request.state, "user_id", None) or settings.current_user_id
    try:
        if isinstance(uid_str, UUID):
            return uid_str
        return UUID(str(uid_str))
    except ValueError:
        # Fallback to a zero-UUID if the configured ID is malformed
        logger.warning("[Auth] Malformed UUID detected: %s. Falling back to zero-UUID.", uid_str)
        return UUID("00000000-0000-0000-0000-000000000000")


class AsyncDBAdapter:
    def __init__(self, sqlite_conn, pg_engine=None):
        self.sqlite_conn = sqlite_conn
        self.pg_engine = pg_engine

    async def fetch_all(self, query: str, params: dict | None = None) -> list[dict]:
        params = params or {}
        def _sync():
            is_local_table = any(t in query for t in [
                "role_implicit_states",
                "role_settings",
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
                "role_settings",
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
                "role_settings",
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

    # ------------------------------------------------------------------
    # M4.4.3 Draft Scheduler 專用 DB 方法
    # ------------------------------------------------------------------

    async def fetch_tracking_logs(self, user_id: str, role_id: str, for_date) -> list:
        """
        [M4.4.3] 撈取特定日期的活動遙測記錄，供草稿生成器彙整。
        from_date = for_date 00:00 ~ for_date+1 00:00 (UTC)。
        """
        from datetime import timedelta
        date_start = str(for_date)
        date_end = str(for_date + timedelta(days=1))
        rows = await self.fetch_all(
            "SELECT id, payload FROM raw_tracking_logs "
            "WHERE user_id = :uid AND role_id = :rid "
            "AND created_at >= :ds AND created_at < :de",
            {"uid": user_id, "rid": role_id, "ds": date_start, "de": date_end},
        )
        import json
        result = []
        for r in rows:
            payload = r.get("payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            from types import SimpleNamespace
            result.append(SimpleNamespace(id=r["id"], payload=payload or {}))
        return result

    async def fetch_elicited_durations(self, user_id: str, role_id: str, for_date) -> list:
        """
        [M4.4.3] 撈取由 M4.4 套問所得的耗時確認（task_slots 中 is_confirmed=true 的項目）。
        """
        from datetime import timedelta
        date_start = str(for_date)
        date_end = str(for_date + timedelta(days=1))
        rows = await self.fetch_all(
            "SELECT project, duration_minutes FROM task_slots "
            "WHERE role_id = :rid AND is_confirmed = 1 "
            "AND created_at >= :ds AND created_at < :de",
            {"rid": role_id, "ds": date_start, "de": date_end},
        )
        return [dict(r) for r in rows]

    async def get_user_active_roles(self, user_id: str) -> list:
        """[M4.4.3] 取得使用者的所有啟用角色。"""
        from types import SimpleNamespace
        rows = await self.fetch_all(
            "SELECT id, display_name FROM roles WHERE user_id = :uid AND is_active = 1",
            {"uid": user_id},
        )
        return [SimpleNamespace(id=r["id"]) for r in rows]

    async def create_draft_reflection(self, **kwargs) -> object:
        """
        [M4.4.3 / RISK-01] 建立日報草稿。is_draft=True, is_reviewed=False 永遠由呼叫端確保。
        """
        import uuid as _uuid
        from types import SimpleNamespace

        reflection_date = str(kwargs.get("reflection_date", ""))
        user_id = kwargs.get("user_id", "")
        role_id = kwargs.get("role_id", "")
        
        # Check if parent daily reflection exists for this date, user, and role
        row = await self.fetch_one(
            "SELECT id FROM daily_reflections "
            "WHERE user_id = :uid AND role_id = :rid AND reflection_date = :rd",
            {"uid": str(user_id), "rid": str(role_id), "rd": reflection_date}
        )
        if row:
            reflection_id = row["id"]
        else:
            reflection_id = str(_uuid.uuid4())
            await self.execute(
                "INSERT INTO daily_reflections "
                "(id, user_id, role_id, reflection_date, is_completed) "
                "VALUES (:id, :uid, :rid, :rd, 0)",
                {"id": reflection_id, "uid": str(user_id), "rid": str(role_id), "rd": reflection_date}
            )

        segment_id = str(_uuid.uuid4())
        ai_description = kwargs.get("ai_description", "")
        ai_analysis = kwargs.get("ai_analysis", "")
        activity_minutes = kwargs.get("activity_minutes", 0)

        if not self.pg_engine:
            # SQLite insertion
            await self.execute(
                "INSERT INTO daily_reflection_segments "
                "(id, reflection_id, user_id, role_id, start_time, end_time, "
                "activity_minutes, ai_description, is_draft, is_reviewed) "
                "VALUES (:id, :ref_id, :uid, :rid, '00:00', '00:00', :mins, :desc, 1, 0)",
                {
                    "id": segment_id,
                    "ref_id": reflection_id,
                    "uid": str(user_id),
                    "rid": str(role_id),
                    "mins": activity_minutes,
                    "desc": ai_description,
                }
            )
        else:
            # PostgreSQL insertion
            await self.execute(
                "INSERT INTO daily_reflection_segments "
                "(id, reflection_id, project, source_type, segment_time, "
                "duration_minutes, ai_description, ai_analysis, is_draft, is_reviewed) "
                "VALUES (:id, :ref_id, 'General', 'monitor', NOW(), :mins, :desc, :anal, TRUE, FALSE)",
                {
                    "id": segment_id,
                    "ref_id": reflection_id,
                    "mins": activity_minutes,
                    "desc": ai_description,
                    "anal": ai_analysis,
                }
            )

        return SimpleNamespace(
            id=reflection_id,
            user_id=kwargs.get("user_id"),
            role_id=kwargs.get("role_id"),
            reflection_date=kwargs.get("reflection_date"),
            ai_description=kwargs.get("ai_description"),
            ai_analysis=kwargs.get("ai_analysis"),
            is_draft=True,
            is_reviewed=False,
            user_feeling=None,
            user_action_plan=None,
            source_log_ids=kwargs.get("source_log_ids"),
        )

    def _get_mock_fallback(self, query: str, params: dict) -> list[dict]:
        """[M0.4] Fallback method. Returning empty list instead of mocks in Phase 5+."""
        return []


# --- module singletons (initialized in lifespan) ---
_debouncer: EventDebouncer | None = None
_gemma_pipeline: GemmaInferencePipeline | None = None
_eguard_filter: EguardFilter | None = None
_drift_shield: DriftShield | None = None
_breakpoint_engine: BreakpointEngine | None = None
_sqlite_conn: sqlite3.Connection | None = None
_db_adapter: AsyncDBAdapter | None = None

# [M4.6] Global SSE broadcast — list of per-client asyncio.Queue instances
_sse_subscribers: list[asyncio.Queue] = []


async def _sse_broadcast(event: dict) -> None:
    """Push an observer event to all currently connected SSE clients."""
    dead = []
    for q in _sse_subscribers:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _sse_subscribers.remove(q)


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
                id              TEXT PRIMARY KEY,
                username        TEXT UNIQUE,
                display_name    TEXT,
                email           TEXT,
                google_id       TEXT,
                google_email    TEXT,
                current_xp      INTEGER DEFAULT 0,
                lifetime_xp     INTEGER DEFAULT 0,
                level           INTEGER DEFAULT 1,
                streak_days     INTEGER DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        # Migration: add google_id and google_email and display_name
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN google_email TEXT")
        except sqlite3.OperationalError:
            pass
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id              TEXT PRIMARY KEY,
                user_id         TEXT NOT NULL,
                slug            TEXT NOT NULL,
                display_name    TEXT NOT NULL,
                color_hex       TEXT,
                icon_name       TEXT,
                avatar_url      TEXT,
                sort_order      INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE(user_id, slug)
            )
        """)
        # Migration: add avatar_url if this table already exists without it
        try:
            cursor.execute("ALTER TABLE roles ADD COLUMN avatar_url TEXT")
        except Exception:
            pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_experts (
                id                  TEXT PRIMARY KEY,
                role_id             TEXT NOT NULL,
                name                TEXT NOT NULL,
                personality_prompt  TEXT,
                backstory           TEXT,
                tone_default        TEXT DEFAULT 'empathetic',
                trust_level         REAL DEFAULT 0.5,
                avatar_url          TEXT,
                is_active           INTEGER DEFAULT 1,
                created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        # [W1] Migration: add persona_card JSON column for PersonaCard v2
        try:
            cursor.execute("ALTER TABLE ai_experts ADD COLUMN persona_card TEXT")
        except Exception:
            pass  # column already exists
        # [Part E] Migration: split title (職稱) from name (姓名)
        try:
            cursor.execute("ALTER TABLE ai_experts ADD COLUMN title TEXT")
        except Exception:
            pass  # column already exists
        # [Part E] Backfill: parse existing name field (e.g. "技術架構師 嚴鋒") → title + name
        cursor.execute("SELECT id, name, persona_card FROM ai_experts WHERE title IS NULL")
        for row in cursor.fetchall():
            row_id, full_name, pc_json = row
            title_val = None
            pure_name = full_name
            # Try persona_card.identity.name for the pure name
            if pc_json:
                try:
                    import json as _json
                    pc = _json.loads(pc_json)
                    identity_name = (pc.get("identity") or {}).get("name")
                    role_title = (pc.get("identity") or {}).get("role")
                    if identity_name:
                        pure_name = identity_name
                        title_val = role_title or None
                except Exception:
                    pass
            # Fallback: split on last space if name looks like "稱謂 姓名"
            if title_val is None and " " in full_name:
                parts = full_name.rsplit(" ", 1)
                if len(parts) == 2 and len(parts[0]) <= 8:
                    title_val = parts[0]
                    pure_name = parts[1]
            cursor.execute(
                "UPDATE ai_experts SET title = ?, name = ? WHERE id = ?",
                (title_val, pure_name, row_id)
            )
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

        # No default user seed — identity is managed in the lifespan identity block below
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_transcripts (
                id          TEXT PRIMARY KEY,
                thread_id   TEXT NOT NULL,
                persona_id  TEXT,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                role_id     TEXT,
                created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_router_rules (
                id            TEXT PRIMARY KEY,
                role_id       TEXT NOT NULL,
                persona_id    TEXT,
                pattern       TEXT NOT NULL,
                target_domain TEXT NOT NULL,
                confidence    REAL DEFAULT 0.50,
                source        TEXT DEFAULT 'manual',
                status        TEXT DEFAULT 'candidate',
                hit_count     INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                last_active   TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intent_logs (
                id              TEXT PRIMARY KEY,
                source_log_id   TEXT,
                role_id         TEXT,
                intent_label    TEXT,
                context_summary TEXT,
                inference_mode  TEXT,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
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
        # Check for existing user in local SQLite (bypass AsyncDBAdapter to avoid routing issues)
        def _get_local_user():
            cur = _sqlite_conn.cursor()
            cur.execute("SELECT id FROM users LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

        user_row = await asyncio.to_thread(_get_local_user)

        if not user_row:
            # First start: generate a fresh persistent UUID for this instance
            instance_user_id = str(uuid.uuid4())
            logger.info("[lifespan] First start detected. Generated new Instance ID: %s", instance_user_id)

            def _insert_local_user():
                cur = _sqlite_conn.cursor()
                cur.execute(
                    "INSERT INTO users (id, username, display_name, email, current_xp, lifetime_xp, level) "
                    "VALUES (?, ?, ?, ?, 0, 0, 1)",
                    (instance_user_id, "local_user", "Me (Local)", f"local_{instance_user_id[:8]}@coos.internal")
                )
                _sqlite_conn.commit()

            await asyncio.to_thread(_insert_local_user)
        else:
            instance_user_id = user_row["id"]
            # Validate it is a proper UUID — regenerate if malformed (e.g. empty string)
            try:
                uuid.UUID(instance_user_id)
            except (ValueError, AttributeError):
                instance_user_id = str(uuid.uuid4())
                logger.warning("[lifespan] Stored ID was malformed, regenerated: %s", instance_user_id)

                def _fix_local_user():
                    cur = _sqlite_conn.cursor()
                    cur.execute("DELETE FROM users")
                    cur.execute(
                        "INSERT INTO users (id, username, display_name, email, current_xp, lifetime_xp, level) "
                        "VALUES (?, ?, ?, ?, 0, 0, 1)",
                        (instance_user_id, "local_user", "Me (Local)", f"local_{instance_user_id[:8]}@coos.internal")
                    )
                    _sqlite_conn.commit()

                await asyncio.to_thread(_fix_local_user)

            logger.info("[lifespan] Using existing Instance ID: %s", instance_user_id)

        # Update settings for this session
        settings.current_user_id = instance_user_id

        # Sync Identity to Cloud (No roles, just the user object)
        if pg_engine and is_cloud_available():
            try:
                with pg_engine.connect() as conn:
                    from sqlalchemy import text
                    conn.execute(text("""
                        INSERT INTO users (id, display_name, email, current_xp, level, streak_days)
                        VALUES (:id, 'Local User', :email, 0, 1, 0)
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        "id": instance_user_id,
                        "email": f"local_{instance_user_id[:8]}@coos.internal"
                    })
                    conn.commit()
                    logger.info("[lifespan] Identity verified with cloud.")
            except Exception as cloud_err:
                logger.warning("[lifespan] Cloud identity sync failed (non-fatal): %s", cloud_err)
    except Exception as e:
        logger.warning("[lifespan] Failed to manage identity: %s", e)

    # [M0.4] Start AsyncLogWriter background flush worker
    from m0_4_logging.writer import get_logger as get_log_writer
    _log_writer = get_log_writer(db_path=str(settings.local_db_path))
    await _log_writer.start()

    # Emit system_startup event to raw_tracking_logs (L1)
    await _log_writer.emit(
        module="M0.3",
        action="system_startup",
        level="INFO",
        payload={"message": "coOS system started"},
        user_id=instance_user_id,
    )

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

                # 2. M4.5 Zombie Cleanup (GAP-B4: use module, not inline SQL)
                # [RISK-13] 僅刪除 is_draft=1 AND is_reviewed=0 AND xp_settled=0 的過期記錄
                from m4_5_xp_settlement.zombie_cleanup import run_zombie_cleanup_sql
                await run_zombie_cleanup_sql(_db_adapter)
            except Exception as e:
                logger.warning("[lifespan] Periodic maintenance failed: %s", e)
            await asyncio.sleep(3600.0)

    maintenance_task = asyncio.create_task(periodic_maintenance())

    # [M4.4.3 SPEC §9] Nightly Draft Cron — 每日 02:00 產出前一日反思草稿
    # [RISK-01] 草稿永遠 is_draft=True, is_reviewed=False，不自動核准
    async def draft_cron_loop():
        from m4_4_elicitation.draft_scheduler import run_draft_cron
        import datetime as _dt

        while True:
            try:
                now = _dt.datetime.now()
                # 計算距離下一個 02:00 的秒數
                target = now.replace(hour=2, minute=0, second=0, microsecond=0)
                if now >= target:
                    target += _dt.timedelta(days=1)
                wait_seconds = (target - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                user_id = settings.current_user_id
                if user_id and _db_adapter:
                    drafts = await run_draft_cron(user_id, db=_db_adapter)
                    if drafts:
                        logger.info("[M4.4.3] Nightly draft cron generated %d draft(s)", len(drafts))
                        await _sse_broadcast({"type": "DRAFT_READY", "count": len(drafts)})
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("[M4.4.3] Draft cron failed: %s", e)
                await asyncio.sleep(3600.0)

    draft_cron_task = asyncio.create_task(draft_cron_loop())

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

    # [M2.2] Start Inference Priority Queue Worker
    from m2_2_gemma.queue import global_inference_queue

    async def inference_worker():
        logger.info("[M2.2] Starting Inference Priority Queue Worker...")
        global_inference_queue._running = True
        try:
            while True:
                try:
                    task = await global_inference_queue.get()
                    if task.fn is None:
                        continue
                    if task.future and task.future.cancelled():
                        continue
                    try:
                        res = await task.fn()
                        if task.future and not task.future.done():
                            task.future.set_result(res)
                    except Exception as exc:
                        if task.future and not task.future.done():
                            task.future.set_exception(exc)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error("[M2.2] Inference worker error: %s", e)
                    await asyncio.sleep(0.5)
        finally:
            global_inference_queue._running = False

    inference_worker_task = asyncio.create_task(inference_worker())

    logger.info("[M0.3] coOS sidecar 啟動完成 (local_only=%s)", not settings.gemini_api_key)
    yield
    # Cleanup
    tunnel_task.cancel()
    for proc in tunnels:
        proc.terminate()
    git_task.cancel()
    maintenance_task.cancel()
    draft_cron_task.cancel()
    inference_worker_task.cancel()
    try:
        await asyncio.gather(git_task, maintenance_task, draft_cron_task, inference_worker_task, return_exceptions=True)
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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse
    from m0_4_logging.writer import get_logger as get_log_writer
    log_writer = get_log_writer()
    payload = {
        "path": request.url.path,
        "method": request.method,
        "detail": exc.detail
    }
    role_id = getattr(request.state, "role_id", None)
    user_id = getattr(request.state, "user_id", None)
    await log_writer.emit_execution_log(
        module="main",
        action="api_http_error",
        level="WARNING" if exc.status_code < 500 else "ERROR",
        message=f"HTTPException {exc.status_code}: {exc.detail}",
        exception_trace=None,
        payload=payload,
        user_id=str(user_id) if user_id else None,
        role_id=str(role_id) if role_id else None
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    from fastapi.responses import JSONResponse
    from m0_4_logging.writer import get_logger as get_log_writer
    log_writer = get_log_writer()
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled exception: %s\n%s", exc, tb_str)
    payload = {
        "path": request.url.path,
        "method": request.method
    }
    role_id = getattr(request.state, "role_id", None)
    user_id = getattr(request.state, "user_id", None)
    await log_writer.emit_execution_log(
        module="main",
        action="unhandled_error",
        level="ERROR",
        message=f"Unhandled exception: {str(exc)}",
        exception_trace=tb_str,
        payload=payload,
        user_id=str(user_id) if user_id else None,
        role_id=str(role_id) if role_id else None
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


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
    user_id = get_safe_user_id(request)
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
        await _drift_shield.verify_input(payload.text, source_path=payload.source_path)
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
    user_id = get_safe_user_id(request)
    
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
    user_id = get_safe_user_id(request)
    
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
    from config import normalize_ipv6_host
    normalized_ai_local_host = normalize_ipv6_host(payload.ai_local_host)
    normalized_ipad_ai_local_host = normalize_ipv6_host(payload.ipad_ai_local_host)

    settings.gemma_model = payload.gemma_model
    settings.ai_local_host = normalized_ai_local_host
    settings.ipad_ai_local_host = normalized_ipad_ai_local_host
    
    # Persist to .env
    update_env_file({
        "gemma_model": payload.gemma_model,
        "ai_local_host": normalized_ai_local_host,
        "ipad_ai_local_host": normalized_ipad_ai_local_host,
    })

    # Log configuration change event
    from m0_4_logging.writer import get_logger as get_log_writer
    await get_log_writer().emit_execution_log(
        module="main",
        action="config_changed",
        level="INFO",
        message="User updated settings and consents",
        payload={
            "theme": payload.theme,
            "notification_enabled": payload.notification_enabled,
            "daily_report_time": payload.daily_report_time,
            "focus_hours_start": payload.focus_hours_start,
            "focus_hours_end": payload.focus_hours_end,
            "gemma_model": payload.gemma_model,
            "ai_local_host": payload.ai_local_host,
            "ipad_ai_local_host": payload.ipad_ai_local_host,
        },
        user_id=str(user_id) if user_id else None,
        role_id=role_id,
    )
    
    return {"status": "success"}

# --- M6.2 Roles & Experts ---

@app.get("/api/m6_2/roles")
async def m6_2_list_roles(request: Request) -> list[dict[str, Any]]:
    """[M6.2] List all roles for the current user."""
    user_id = str(get_safe_user_id(request))
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
            "slug": r["slug"],
            "avatarUrl": r.get("avatar_url"),
        } for r in rows
    ]


@app.post("/api/m6_2/roles")
async def m6_2_create_role(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """[M6.2] Create a new role."""
    user_id = str(get_safe_user_id(request))
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")

    import uuid
    role_id = str(uuid.uuid4())
    slug = name.lower().replace(" ", "_")

    await _db_adapter.execute(
        "INSERT INTO roles (id, user_id, slug, display_name, color_hex, icon_name, avatar_url, sort_order) "
        "VALUES (:id, :uid, :slug, :name, :color, :icon, :avatar, :sort)",
        {
            "id": role_id,
            "uid": str(user_id),
            "slug": slug,
            "name": name,
            "color": body.get("color", "#999999"),
            "icon": body.get("icon", "activity"),
            "avatar": body.get("avatar_url"),
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
            "title": r["title"] if "title" in r.keys() else None,
            "personalityPrompt": r["personality_prompt"],
            "trustLevel": r["trust_level"],
            "avatarUrl": r["avatar_url"],
        } for r in rows
    ]


@app.post("/api/m6_2/roles/{role_id}/experts")
async def m6_2_create_expert(role_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """[M6.2] Create a new AI expert for a role."""
    import uuid
    expert_id = str(uuid.uuid4())
    name = body.get("name", "AI 助手")
    personality_prompt = body.get("personality_prompt", "")
    tone = body.get("tone_default", "empathetic")
    backstory = body.get("backstory", "")
    domain = body.get("domain", "")

    await _db_adapter.execute(
        "INSERT INTO ai_experts (id, role_id, name, personality_prompt, backstory, tone_default, trust_level, is_active) "
        "VALUES (:id, :rid, :name, :pp, :bs, :tone, 0.5, 1)",
        {
            "id": expert_id,
            "rid": role_id,
            "name": name,
            "pp": personality_prompt,
            "bs": backstory,
            "tone": tone,
        }
    )
    return {
        "id": expert_id,
        "expertName": name,
        "personalityPrompt": personality_prompt,
        "trustLevel": 0.8,
        "avatarUrl": None,
        "domain": domain,
    }


@app.delete("/api/m6_2/roles/{role_id}")
async def m6_2_delete_role(role_id: str, request: Request) -> dict[str, Any]:
    """[M6.2] Soft-delete a role."""
    user_id = str(get_safe_user_id(request))
    await _db_adapter.execute(
        "UPDATE roles SET is_active = 0 WHERE id = :rid AND user_id = :uid",
        {"rid": role_id, "uid": str(user_id)}
    )
    return {"status": "deleted"}


# --- Monitored Apps Whitelist ---

@app.get("/api/settings/whitelist")
async def get_app_whitelist(request: Request) -> list[str]:
    """[M1.1] Fetch the current monitored apps whitelist."""
    user_id = get_safe_user_id(request)
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
    user_id = get_safe_user_id(request)
    
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


# --- Google OAuth Stubs (L3 identity — future multi-device sync) ---
# Architecture: Google OAuth token is only stored as a foreign key reference.
# The google_id + google_email are stored in the LOCAL users table (L1).
# The cloud PostgreSQL users table only receives an upsert with the google_id
# once consent is granted. Raw OAuth tokens are never persisted.

@app.get("/api/auth/google/url")
async def google_auth_url() -> dict[str, Any]:
    """Return the Google OAuth authorization URL for the client to open in browser."""
    from config import get_settings as _gs
    s = _gs()
    client_id = getattr(s, "google_client_id", "") or ""
    if not client_id:
        # Stub mode: return a placeholder URL so the UI can show a disabled state
        return {"url": None, "stub": True, "message": "Google OAuth not configured (GOOGLE_CLIENT_ID missing)"}
    redirect_uri = f"http://localhost:{s.fastapi_port}/api/auth/google/callback"
    scope = "openid email profile"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return {"url": url, "stub": False}


@app.get("/api/auth/google/callback")
async def google_auth_callback(code: str, request: Request) -> dict[str, Any]:
    """Handle Google OAuth callback: exchange code → store google_id + email locally."""
    from config import get_settings as _gs
    s = _gs()
    client_id = getattr(s, "google_client_id", "") or ""
    client_secret = getattr(s, "google_client_secret", "") or ""
    if not client_id or not client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    import httpx
    redirect_uri = f"http://localhost:{s.fastapi_port}/api/auth/google/callback"
    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        token_resp.raise_for_status()
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    google_id = userinfo.get("id", "")
    google_email = userinfo.get("email", "")
    display_name = userinfo.get("name", "")

    # Store google_id + email in local users table (L1 — never raw token)
    user_id = settings.current_user_id
    def _link_google():
        cur = _sqlite_conn.cursor()
        cur.execute(
            "UPDATE users SET google_id = ?, google_email = ?, display_name = ? WHERE id = ?",
            (google_id, google_email, display_name, user_id)
        )
        _sqlite_conn.commit()
    await asyncio.to_thread(_link_google)

    logger.info("[Auth] Google account linked: %s -> user %s", google_email, user_id)
    return {"status": "linked", "google_email": google_email, "display_name": display_name}


@app.get("/api/auth/google/status")
async def google_auth_status(request: Request) -> dict[str, Any]:
    """Return whether current local user has a linked Google account."""
    user_id = settings.current_user_id
    def _get_google():
        cur = _sqlite_conn.cursor()
        cur.execute("SELECT google_id, google_email, display_name FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    row = await asyncio.to_thread(_get_google)
    if row and row.get("google_id"):
        return {"linked": True, "google_email": row["google_email"], "display_name": row["display_name"]}
    return {"linked": False}


# --- M6.3 Role Context ---

@app.get("/api/m6_3/role_context")
async def m6_3_role_context(role_id: str, request: Request) -> dict[str, Any]:
    """Context Header 四槽位資料 (Project / Role / Promises / Goal)"""
    user_id = get_safe_user_id(request)
    
    import uuid
    if isinstance(role_id, str):
        try:
            role_uuid = uuid.UUID(role_id)
        except ValueError:
            role_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, role_id)
    else:
        role_uuid = uuid.uuid4()
        
    role_ctx = await build_role_context(user_id=user_id, role_id=role_uuid, db=_db_adapter)

    # [D3] Return full projects list so Project board can show all active projects
    projects_list = [
        {
            "name": p.get("name", ""),
            "description": p.get("description") or "",
            "created_at": p.get("created_at") or "",
        }
        for p in role_ctx.projects
    ]
    # Legacy single-project field kept for backward compat
    project = {"name": role_ctx.projects[0].get("name")} if role_ctx.projects else {"name": "無作用中專案"}

    role_row = await _db_adapter.fetch_one("SELECT display_name FROM roles WHERE id = :rid", {"rid": str(role_uuid)})
    role_name = role_row["display_name"] if role_row else "Role"
    role = {"name": role_name}

    promises = [p.get("text") for p in role_ctx.upcoming_promises]
    goals = [g.get("title") for g in role_ctx.active_goals]

    return {
        "role_id": str(role_id),
        "project": project,
        "projects": projects_list,
        "role": role,
        "promises": promises,
        "goals": goals,
    }


# --- M6.4 Daily Reflections ---

@app.get("/api/m6_4/heatmap")
async def m6_4_heatmap(request: Request, role_id: str) -> list[dict[str, Any]]:
    """過去 365 天的活躍度熱圖資料 (Real Data)"""
    user_id = get_safe_user_id(request)
    
    # [M6.4] Query real daily reflections count grouped by date for the last 365 days
    query = """
        SELECT date(created_at) as event_date, COUNT(*) as count
        FROM daily_reflections
        WHERE user_id = :uid AND role_id = :rid
          AND created_at >= date('now', '-365 days')
        GROUP BY date(created_at)
        ORDER BY event_date ASC
    """
    rows = await _db_adapter.fetch_all(query, {"uid": str(user_id), "rid": role_id})
    
    return [{"date": row["event_date"], "count": row["count"]} for row in rows]


@app.get("/api/m6_4/daily_timeline")
async def m6_4_daily_timeline(request: Request, date: str, role_id: str | None = None) -> list[dict[str, Any]]:
    """當日任務清單（依角色分組）"""
    user_id = get_safe_user_id(request)
    
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

    if _db_adapter:
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
                    "WHERE reflection_id = :rid",
                    {"rid": str(r.get("id"))}
                )
                for s in segments:
                    timeline.append({
                        "id": str(s.get("id")),
                        "roleId": role_id or str(r.get("role_id")),
                        "roleName": "Role",
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
            return timeline
        except Exception as e:
            logger.warning("[daily_timeline] Failed to fetch timeline from PG: %s", e)

    return []


@app.patch("/api/m6_4/reflections/{reflection_id}")
async def m6_4_patch_reflection(reflection_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """[RISK-01] 更新 user_feeling / user_action_plan / is_reviewed"""
    logger.info("[M6.4] reflection %s patched: %s", reflection_id, list(body.keys()))
    
    if _db_adapter:
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
    
    user_id = get_safe_user_id(request)
    
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
    user_id = get_safe_user_id(request)
    
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
    user_id = get_safe_user_id(request)
    
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


async def _resolve_session_thread_id(role_id: str, thread_id: str, create_if_new: bool = False) -> str:
    """Resolve the latest active thread_id segment.
    If create_if_new is True, it starts a new thread ID segment if the last message
    was more than 30 minutes (1800 seconds) ago.
    """
    prefix = f"{thread_id}_%"
    row = await _db_adapter.fetch_one(
        "SELECT thread_id, created_at FROM chat_transcripts "
        "WHERE role_id = :rid AND (thread_id = :tid OR thread_id LIKE :prefix) "
        "ORDER BY created_at DESC LIMIT 1",
        {"rid": role_id, "tid": thread_id, "prefix": prefix}
    )
    if not row:
        if create_if_new:
            import uuid
            return f"{thread_id}_{uuid.uuid4().hex[:8]}"
        return thread_id

    last_thread_id = row["thread_id"]
    last_created_at = row["created_at"]

    if create_if_new:
        from datetime import datetime, timezone
        try:
            clean_time = last_created_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_time)
        except Exception:
            return last_thread_id
        
        now = datetime.now(timezone.utc)
        diff = (now - dt).total_seconds()
        if diff > 1800:
            import uuid
            new_tid = f"{thread_id}_{uuid.uuid4().hex[:8]}"
            logger.info("[ThreadSplit] Inactivity timeout (diff=%.1fs > 1800s). Splitting thread from %s to %s", diff, last_thread_id, new_tid)
            return new_tid

    return last_thread_id


@app.get("/api/m4_1/history")
async def m4_1_history(role_id: str, thread_id: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
    """回傳指定角色（或特定 thread）的最近聊天紀錄，按時間排序。"""
    if thread_id:
        resolved_tid = await _resolve_session_thread_id(role_id, thread_id, create_if_new=False)
        rows = await _db_adapter.fetch_all(
            "SELECT role, content, persona_id, thread_id, created_at FROM chat_transcripts "
            "WHERE role_id = :rid AND thread_id = :tid ORDER BY created_at DESC LIMIT :lim",
            {"rid": role_id, "tid": resolved_tid, "lim": limit},
        )
    else:
        rows = await _db_adapter.fetch_all(
            "SELECT role, content, persona_id, thread_id, created_at FROM chat_transcripts "
            "WHERE role_id = :rid ORDER BY created_at DESC LIMIT :lim",
            {"rid": role_id, "lim": limit},
        )
    return [dict(r) for r in reversed(rows)]


@app.get("/api/m4_1/threads")
async def m4_1_threads(role_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """回傳角色下所有 thread，供前端顯示聊天室清單。"""
    rows = await _db_adapter.fetch_all(
        "SELECT DISTINCT thread_id, persona_id, MAX(created_at) as last_at "
        "FROM chat_transcripts WHERE role_id = :rid "
        "GROUP BY thread_id, persona_id ORDER BY last_at DESC LIMIT :lim",
        {"rid": role_id, "lim": limit},
    )
    return [dict(r) for r in rows]


@app.post("/api/m4_1/chat")
async def m4_1_chat(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    """對話端點 — 串接 LangGraph 多智能體頂層協調與 Persona 狀態機"""
    user_msg = body.get("content", "")
    role_id = body.get("role_id", "")
    thread_id = body.get("thread_id")
    # 前端明確指定的 persona_id（expert 聊天室時傳入），優先於 routing engine
    requested_persona_id = body.get("persona_id")
    
    # [M2.3 DRIFT Shield] Security check
    try:
        await _drift_shield.verify_input(user_msg)
    except Exception as e:
        logger.warning("[M2.3] DRIFT blocked chat input: %s", e)
        return {"content": "對不起，我偵測到輸入內容可能存在安全風險，已暫時阻斷處理。", "persona_id": "system"}

    # [M2.3 Eguard Filter] PII Masking before processing
    sanitized = _eguard_filter.mask_pii(user_msg, role_id=str(role_id))
    user_msg = sanitized.sanitized_text

    user_id = get_safe_user_id(request)
    
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
            
    # Use thread_id from frontend and resolve it dynamically to handle inactivity splitting
    if thread_id:
        resolved_thread_id = await _resolve_session_thread_id(str(role_uuid), thread_id, create_if_new=True)
    else:
        resolved_thread_id = f"thread_{role_uuid}"
        
    # 拉近期對話歷史（最多 12 條）供工具型 AI 保持連貫
    # DESC LIMIT 12 取最新 12 條，再反轉為時間正序送入 LLM context
    chat_history: list[dict] = []
    try:
        history_rows = await _db_adapter.fetch_all(
            "SELECT role, content FROM chat_transcripts "
            "WHERE thread_id = :tid ORDER BY created_at DESC LIMIT 12",
            {"tid": resolved_thread_id},
        )
        chat_history = [{"role": r["role"], "content": r["content"]} for r in reversed(history_rows)]
    except Exception as e:
        logger.debug("[M4.1] Failed to load chat history: %s", e)

    router_input = {
        "thread_id": resolved_thread_id,
        "role_id": str(role_uuid),
        "user_message": user_msg,
        "chat_history": chat_history,
        "intent_vector": intent_vector,
        "active_experts": role_ctx.active_experts,
        "role_rules": [],
        "implicit_state": role_ctx.implicit_state.get("implicit_state") if role_ctx.implicit_state else None,
        "active_goals": role_ctx.active_goals,
        "upcoming_promises": role_ctx.upcoming_promises,
    }

    # 若前端明確指定了 expert persona_id，直接注入 route_decision，跳過 rule_router
    # [RISK-06] 仍驗證該 persona 確實屬於此 role
    if requested_persona_id and requested_persona_id not in ("__tool__", "tool_ai_default"):
        expert_in_role = next(
            (e for e in role_ctx.active_experts if str(e.get("id")) == requested_persona_id),
            None,
        )
        if expert_in_role:
            router_input["route_decision"] = {
                "persona_id": requested_persona_id,
                "route_reason": "frontend_explicit",
                "confidence": 1.0,
                "thread_id": resolved_thread_id,
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
            "thread_id": resolved_thread_id,
            "suggest_match": False,
        }

    persona_id = (res.get("route_decision") or {}).get("persona_id") or "tool_ai_default"
    reply = res.get("persona_response") or "我在聽，你繼續說說看？"
    suggest_match = bool(res.get("suggest_match", False))
    split_messages = res.get("split_messages") or []  # [W6] 多氣泡序列

    # [GAP-B5] M4.6 project detection は M4.1 invoke_persona_node の
    # _dispatch_observer_bg に一本化（二重検出を廃止）。
    # observer_deps._resolve_sse() が _sse_broadcast に接続済み（GAP-C1 修復）。

    # [M4.4] Natural Elicitation Injection
    # [R08 §五 微干預原則] 套問以獨立訊息氣泡注入，而非黏在主回覆（SPEC §7 inject_messages）
    # confidence >= 0.7 的時段不觸發（SPEC §8 「AI 裝傻」反模式）
    elicitation_messages: list[str] = []
    try:
        from m4_4_elicitation.controller import ElicitationController, CONFIDENCE_THRESHOLD
        if not hasattr(app.state, "elicitation_controller"):
            app.state.elicitation_controller = ElicitationController()
        # conversation_turn_counter 記錄真實對話 turn 數（非注入次數）
        if not hasattr(app.state, "conversation_turn_counter"):
            app.state.conversation_turn_counter = {}

        ec = app.state.elicitation_controller

        # 每次對話都計 turn（不管是否套問）
        conv_turn = app.state.conversation_turn_counter.get(resolved_thread_id, 0)
        app.state.conversation_turn_counter[resolved_thread_id] = conv_turn + 1

        from m4_6_observer.project_detector import regex_extract_project

        detected_name = regex_extract_project(user_msg)
        if not detected_name:
            projects = await _db_adapter.fetch_all(
                "SELECT name FROM role_projects WHERE role_id = :rid ORDER BY created_at DESC LIMIT 1",
                {"rid": str(role_uuid)}
            )
            if projects:
                detected_name = projects[0]["name"]

        if detected_name:
            # 依尚未觸發的 context 類型輪替（每種最多 1 次，DEVIATION-01 拍板）
            all_contexts = ["general_duration", "goal_probe", "deadline_probe"]
            used_ctxs = {ctx for _, ctx in ec._history.get(resolved_thread_id, [])}
            next_context = next((c for c in all_contexts if c not in used_ctxs), None)

            if next_context and ec.can_elicit(resolved_thread_id, conv_turn, context=next_context):
                fragment = ec.generate_elicitation(
                    context=next_context,
                    role_id=str(role_uuid),
                    project_name=detected_name,
                )
                if fragment.inject_messages:
                    elicitation_messages = fragment.inject_messages
                    ec.record_elicitation(resolved_thread_id, conv_turn, context=next_context)
    except Exception as e:
        logger.warning("[M4.4] Elicitation injection failed: %s", e)

    # Persist chat transcript
    try:
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
                "role_id": str(role_uuid),
            },
        )
        await _db_adapter.execute(
            "INSERT INTO chat_transcripts (id, thread_id, persona_id, role, content, role_id) "
            "VALUES (:id, :thread_id, :persona_id, 'assistant', :content, :role_id)",
            {
                "id": reply_id,
                "thread_id": resolved_thread_id,
                "persona_id": persona_id,
                "content": reply,
                "role_id": str(role_uuid),
            },
        )
    except Exception as e:
        logger.error("Failed to save chat transcript to SQLite: %s", e)

    return {
        "content": reply,
        "persona_id": persona_id,
        "thread_id": resolved_thread_id,
        "suggest_match": suggest_match,
        "elicitation_messages": elicitation_messages,  # [M4.4 SPEC §7] 獨立氣泡序列，前端依序渲染
        "split_messages": split_messages,  # [W6] 多氣泡序列 [{content, delay_ms}]
    }


async def _ai_generate_expert(user_description: str, role_id: str) -> dict | None:
    """用 Gemini 根據使用者描述自動生成一位具備固定人設的 AI 專家，存入 ai_experts 並回傳。
    [M4.2 SPEC §7.1] Persona 必須具備具體過往經歷，禁止通用 AI 語氣。
    [R03 §1] BDI 結構人設：belief (背景知識)、desire (助人目標)、intention (溝通風格)。
    [R05 §跨越恐怖谷] 副語言線索注入在 personality_prompt 中定義。
    """
    from m4_1_router.routing_engine import PERSONA_MODEL, PERSONA_MODEL_FALLBACK, get_cloud_llm_client, RateLimitError, ServiceUnavailableError
    import uuid, json

    # [W2] PersonaCard v2 結構化生成 prompt
    prompt = f"""你是一個 AI 顧問角色生成器，專門設計具備真實感的 AI 專家夥伴。
根據以下使用者需求，生成一位有具體過往經歷的 AI 顧問。

使用者描述：「{user_description}」

設計要求：
- 角色必須有具體的出生年代、求學/工作背景
- 禁止使用「我是AI」「我會盡力協助」等通用語句
- 個性要有缺點和偏好
- 語氣要符合 tone_default 的定義
- 必須有明確的專業邊界（知道什麼、不知道什麼）
- 要有 2-3 個個人立場（stances），代表此角色在專業議題上的堅定見解

請用 JSON 回傳（只回 JSON，不要其他文字）：
{{
  "name": "稱謂+姓名（如：動力導師 Robert、學姐 孟婷）",
  "identity": {{
    "name": "同上",
    "birth_year": 1988,
    "education": "台大資工畢業",
    "career": "曾在新創任 PM 五年，現自己開公司"
  }},
  "big_five": {{"O": 0.7, "C": 0.8, "E": 0.5, "A": 0.6, "N": 0.3}},
  "speech_profile": {{
    "fillers": ["嗯", "欸"],
    "口頭禪": "一句常用的口頭禪",
    "sentence_length": "short"
  }},
  "formative_episodes": [
    {{"age": 22, "event": "一個具體人生經歷", "impact": "對其影響"}}
  ],
  "knowledge_boundary": {{
    "expert_in": ["領域1", "領域2"],
    "ignorant_of": ["不擅長的領域"]
  }},
  "stances": [
    {{"topic": "一個議題", "position": "此角色的立場"}}
  ],
  "personality_prompt": "完整人設描述，300字以內。包含：1)出生年代與具體學經歷 2)個性特徵（含缺點） 3)溝通風格與口頭禪 4)對此類問題的個人見解",
  "backstory": "一句話背景",
  "tone_default": "empathetic 或 authoritative 或 coaching（三選一）",
  "domain": "主要領域英文標籤（如 coding, study, career, emotion, productivity, creative）",
  "domain_keywords": ["中文關鍵字1", "中文關鍵字2", "中文關鍵字3"]
}}"""

    raw = None
    for model in (PERSONA_MODEL, PERSONA_MODEL_FALLBACK):
        try:
            client = get_cloud_llm_client(model)
            raw = await client.complete(prompt, max_output_tokens=2048, temperature=0.8)
            break
        except (RateLimitError, ServiceUnavailableError) as e:
            logger.warning("[match_persona] auto-generate expert model %s failed: %s", model, e)

    if not raw:
        try:
            from m0_4_logging.writer import get_logger as get_log_writer
            await get_log_writer().emit_execution_log(
                module="M4.2",
                action="expert_generation_failed",
                level="ERROR",
                message="LLM failed to return a response for expert generation",
                payload={"user_description": user_description},
                user_id=settings.current_user_id,
                role_id=role_id
            )
        except Exception:
            pass
        return None

    try:
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned.strip())
    except Exception as e:
        logger.warning("[match_persona] failed to parse expert JSON: %s | raw=%s", e, raw[:200])
        try:
            from m0_4_logging.writer import get_logger as get_log_writer
            log_writer = get_log_writer()
            await log_writer.emit_execution_log(
                module="M4.2",
                action="expert_generation_parse_failed",
                level="ERROR",
                message=f"Failed to parse expert JSON: {str(e)}",
                payload={"raw_response": raw},
                user_id=settings.current_user_id,
                role_id=role_id
            )
        except Exception:
            pass
        return None

    expert_id = str(uuid.uuid4())
    # [Part E] Split title (職稱) from name (姓名) via persona_card.identity
    _identity = data.get("identity") or {}
    name = _identity.get("name") or data.get("name", "AI 助手")
    title = _identity.get("role") or None
    # Fallback: if name still contains a space prefix (e.g. "技術架構師 嚴鋒"), split it
    if not title and " " in name:
        _parts = name.rsplit(" ", 1)
        if len(_parts) == 2 and len(_parts[0]) <= 8:
            title, name = _parts[0], _parts[1]
    personality_prompt = data.get("personality_prompt", "")
    backstory = data.get("backstory", "")
    tone = data.get("tone_default", "empathetic")
    domain = data.get("domain", "general")
    domain_keywords: list = data.get("domain_keywords", [])

    # [GAP-C5] 禁用語檢查與程式化修復：personality_prompt / backstory 不得含通用 AI 語氣
    _FORBIDDEN_PHRASES = [
        "我是AI", "我是一個AI", "我是人工智慧", "我會盡力協助", "作為AI助手",
        "I am an AI", "I'm an AI", "I am a helpful", "as an AI assistant",
        "我沒有個人意見", "我無法提供", "我只是個",
    ]
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in personality_prompt:
            logger.warning("[GAP-C5] Sanitizing forbidden phrase '%s' from personality_prompt", phrase)
            personality_prompt = personality_prompt.replace(phrase, "")
        if phrase in backstory:
            logger.warning("[GAP-C5] Sanitizing forbidden phrase '%s' from backstory", phrase)
            backstory = backstory.replace(phrase, "")

    # [GAP-C5] 具體性檢查與程式化補救：personality_prompt 需包含年代/學經歷等具體資訊
    _CONCRETENESS_MARKERS = ["年生", "年出生", "畢業", "工作", "曾在", "任職", "經歷", "學過", "born", "graduated", "worked at"]
    has_concrete_identity = any(marker in personality_prompt for marker in _CONCRETENESS_MARKERS)
    if not has_concrete_identity:
        logger.warning("[GAP-C5] Expert generation warning: personality_prompt lacks concrete identity markers, auto-injecting default background.")
        edu = data.get("identity", {}).get("education", "相關專業")
        career = data.get("identity", {}).get("career", "多年實務經歷")
        birth = data.get("identity", {}).get("birth_year", 1990)
        personality_prompt += f" 他出生於 {birth} 年，畢業於 {edu}，在行業中擁有 {career} 的工作經歷。"

    # Clamp tone to valid values
    if tone not in ("empathetic", "authoritative", "coaching"):
        tone = "empathetic"

    # [W2] PersonaCard v2: 嘗試校驗與編譯
    persona_card_json = None
    try:
        from m4_2_persona.persona_card import persona_card_from_dict, compile_to_prompt, critic_check
        card = persona_card_from_dict(data)
        passed, issue_list = critic_check(card)
        if passed:
            compiled = compile_to_prompt(card)
            personality_prompt = compiled  # 以編譯後的結構化 prompt 取代原始文字
            persona_card_json = json.dumps(data, ensure_ascii=False)
            logger.info("[W2] PersonaCard v2 validated for '%s' (%d issues)", name, len(issue_list))
        else:
            logger.warning("[W2] PersonaCard critic failed (%d issues), using raw prompt", len(issue_list))
    except Exception as e:
        logger.warning("[W2] PersonaCard compilation fallback: %s", e)

    # [R05 §跨越恐怖谷 §治療同盟] trust_level 從 0.5 起跳，隨互動累積信任後升級
    await _db_adapter.execute(
        "INSERT INTO ai_experts (id, role_id, name, title, personality_prompt, backstory, tone_default, trust_level, is_active, persona_card) "
        "VALUES (:id, :rid, :name, :title, :pp, :bs, :tone, 0.5, 1, :pc)",
        {"id": expert_id, "rid": role_id, "name": name, "title": title, "pp": personality_prompt, "bs": backstory, "tone": tone, "pc": persona_card_json}
    )

    # [SPEC §7.5] 自動生成對應的路由規則種子 (domain_keywords → role_router_rules)
    if domain_keywords:
        import re as _re
        pattern = "|".join(_re.escape(kw) for kw in domain_keywords[:5])
        await _db_adapter.execute(
            "INSERT OR IGNORE INTO role_router_rules "
            "(id, role_id, persona_id, pattern, target_domain, confidence, source, status) "
            "VALUES (:id, :rid, :pid, :pattern, :domain, 0.80, 'auto_generated', 'active')",
            {
                "id": str(uuid.uuid4()),
                "rid": role_id,
                "pid": expert_id,
                "pattern": pattern,
                "domain": domain,
            }
        )

    try:
        from m0_4_logging.writer import get_logger as get_log_writer
        await get_log_writer().emit_execution_log(
            module="M4.2",
            action="expert_generated",
            level="INFO",
            message=f"Successfully generated new expert: {name} ({domain})",
            payload={
                "expert_id": expert_id,
                "name": name,
                "domain": domain,
                "sanitized_forbidden": [p for p in _FORBIDDEN_PHRASES if p in data.get("personality_prompt", "") or p in data.get("backstory", "")],
                "injected_concrete_identity": not has_concrete_identity
            },
            user_id=settings.current_user_id,
            role_id=role_id
        )
    except Exception:
        pass

    logger.info("[match_persona] auto-generated expert '%s' (%s) for role %s", name, domain, role_id)
    return {"id": expert_id, "name": name, "personality_prompt": personality_prompt, "tone_default": tone, "domain": domain}


@app.post("/api/m4_1/match_persona")
async def m4_1_match_persona(body: dict[str, Any]) -> dict[str, Any]:
    """配對最合適的 Persona；若角色尚無專家則先用 AI 自動生成一位。"""
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

    try:
        from m0_4_logging.writer import get_logger as get_log_writer
        await get_log_writer().emit_execution_log(
            module="M4.1",
            action="match_request",
            level="INFO",
            message=f"Received matchmaking request for role {role_id}",
            payload={
                "user_msg": user_msg,
                "exclude_persona_id": exclude_persona_id,
                "active_experts_count": len(active_experts)
            },
            user_id=settings.current_user_id,
            role_id=str(role_uuid)
        )
    except Exception:
        pass

    # 若此角色尚無任何專家，用 AI 自動生成一位
    auto_generated_expert: dict | None = None
    if not active_experts and user_msg:
        auto_generated_expert = await _ai_generate_expert(user_msg, str(role_uuid))
        if auto_generated_expert:
            active_experts = [auto_generated_expert]

    from m4_1_router.routing_engine import RouteDecision, route_with_confidence
    import uuid as _uuid

    # 若只有剛自動生成的單一專家，直接配對（跳過 routing engine 避免 fallback 到 tool_ai）
    if auto_generated_expert and len(active_experts) == 1:
        decision = RouteDecision(
            persona_id=auto_generated_expert["id"],
            route_reason="auto_generated",
            thread_id=str(_uuid.uuid4()),
            confidence=0.9,
        )
    else:
        decision = await route_with_confidence(
            user_msg=user_msg,
            intent_vector={},
            active_experts=active_experts,
            role_id=str(role_uuid),
            role_rules=[],
        )
        # 若已有專家但無任何專家符合要求（低於配對閥值 0.80 或 fallback），則自動生成全新專家
        if (decision.persona_id == "tool_ai_default" or decision.confidence < 0.80) and user_msg:
            new_expert = await _ai_generate_expert(user_msg, str(role_uuid))
            if new_expert:
                decision = RouteDecision(
                    persona_id=new_expert["id"],
                    route_reason="auto_generated",
                    thread_id=str(_uuid.uuid4()),
                    confidence=0.9,
                )

    matched = decision.persona_id is not None and decision.persona_id != "tool_ai_default"

    try:
        from m0_4_logging.writer import get_logger as get_log_writer
        await get_log_writer().emit_execution_log(
            module="M4.1",
            action="match_decision",
            level="INFO",
            message=f"Match decision: {decision.persona_id} (confidence: {decision.confidence:.2f}, reason: {decision.route_reason})",
            payload={
                "matched_persona_id": decision.persona_id,
                "confidence": decision.confidence,
                "route_reason": decision.route_reason,
                "fallback_to_generation": (decision.persona_id == "tool_ai_default" or decision.confidence < 0.80) and bool(user_msg)
            },
            user_id=settings.current_user_id,
            role_id=str(role_uuid)
        )
    except Exception:
        pass

    # [DEVIATION-05 / R09 §SDT] 回傳候選專家 preview，讓使用者先確認（自主感）
    # 實際問候在 /api/m4_1/confirm_match 由 M4.2 graph 以 persona 語氣生成並落地 transcripts
    expert_preview: dict | None = None
    if matched and decision.persona_id:
        expert_row = await _db_adapter.fetch_one(
            "SELECT id, name, personality_prompt, backstory, tone_default FROM ai_experts WHERE id = :eid",
            {"eid": decision.persona_id}
        )
        if not expert_row:
            for e in active_experts:
                if e.get("id") == decision.persona_id:
                    expert_row = {
                        "id": e["id"],
                        "name": e["name"],
                        "personality_prompt": e.get("personality_prompt", ""),
                        "backstory": e.get("backstory", ""),
                        "tone_default": e.get("tone_default", "empathetic"),
                    }
                    break
        if expert_row:
            expert_preview = {
                "id": expert_row["id"],
                "name": expert_row["name"],
                "backstory": expert_row.get("backstory") or "",
                "tone_default": expert_row.get("tone_default", "empathetic"),
                "personality_summary": (expert_row.get("personality_prompt") or "")[:80],
            }

    return {
        "persona_id": decision.persona_id,
        "matched": matched,
        "reason": decision.route_reason,
        "expert_preview": expert_preview,
        # greeting_message 已移至 /api/m4_1/confirm_match（persona 化 + 落地 transcripts）
    }


@app.post("/api/m4_1/confirm_match")
async def m4_1_confirm_match(body: dict[str, Any]) -> dict[str, Any]:
    """
    [DEVIATION-05] 使用者在 preview 卡確認配對後，觸發 persona 化問候並落地 chat_transcripts。
    [R09 §SDT] 確認後才生成問候，保留使用者自主感（「是我選的」）。
    [R03 §1] 問候由 M4.2 persona graph 生成，保持人設語氣一致性。
    """
    persona_id = body.get("persona_id", "")
    role_id = body.get("role_id", "")
    user_msg = body.get("original_message", "")  # 配對時的原始訊息，提供問候語境

    if not persona_id or not role_id:
        raise HTTPException(status_code=422, detail="persona_id and role_id are required")

    import uuid as _uuid

    try:
        role_uuid = _uuid.UUID(role_id)
    except ValueError:
        role_uuid = _uuid.uuid5(_uuid.NAMESPACE_DNS, role_id)

    try:
        from m0_4_logging.writer import get_logger as get_log_writer
        await get_log_writer().emit_execution_log(
            module="M4.1",
            action="confirm_match_start",
            level="INFO",
            message=f"Confirm match request received for persona {persona_id}",
            payload={
                "persona_id": persona_id,
                "role_id": role_id,
                "original_message": user_msg
            },
            user_id=settings.current_user_id,
            role_id=role_id
        )
    except Exception:
        pass

    # 取專家資料
    expert_row = await _db_adapter.fetch_one(
        "SELECT id, name, personality_prompt, backstory, tone_default, trust_level FROM ai_experts WHERE id = :eid",
        {"eid": persona_id}
    )
    if not expert_row:
        raise HTTPException(status_code=404, detail="Expert not found")

    thread_id = await _resolve_session_thread_id(str(role_uuid), f"thread_{role_uuid}_{persona_id}", create_if_new=True)

    # 呼叫 M4.2 persona graph 以 persona 語氣生成問候
    greeting_text: str | None = None
    try:
        from m4_2_persona.graph import get_persona_graph

        # [R05 §治療同盟] 初次問候要短、像真人：一句簡短自我介紹 + 一個開放問題，不交代完整背景
        greeting_prompt = (
            "（系統提示：這是你和使用者的第一句話。請用你的人設語氣"
            "「簡短」地打招呼並自我介紹一句，然後問一個輕鬆的開放問題。"
            "務必簡短自然，像真人傳訊息，不要一次交代你的完整學經歷或背景。"
            f"使用者剛剛說的是：「{user_msg[:60]}」）"
        )
        persona_input = {
            "thread_id": thread_id,
            "role_id": str(role_uuid),
            "user_message": greeting_prompt,
            "persona_id": persona_id,
            "persona_config": {
                "name": expert_row["name"],
                "personality_prompt": expert_row.get("personality_prompt"),
                "backstory": expert_row.get("backstory"),
                "tone_default": expert_row.get("tone_default", "empathetic"),
                "trust_level": expert_row.get("trust_level", 0.5),
            },
            "chat_history": [],
            "bdi_belief": "",
            "bdi_desire": "",
            "current_tone": expert_row.get("tone_default", "empathetic"),
            "current_agency": expert_row.get("trust_level", 0.5),
        }
        persona_graph = get_persona_graph()
        res = await persona_graph.ainvoke(persona_input)
        greeting_text = res.get("final_response") or res.get("raw_response")
    except Exception as e:
        logger.warning("[confirm_match] persona graph greeting failed: %s", e)

    try:
        from m0_4_logging.writer import get_logger as get_log_writer
        await get_log_writer().emit_execution_log(
            module="M4.1",
            action="confirm_match_greeting",
            level="INFO" if greeting_text else "WARNING",
            message="Greeting generated by persona graph" if greeting_text else "Greeting generation failed, using fallback",
            payload={
                "persona_id": persona_id,
                "greeting_text": greeting_text,
                "used_fallback": not greeting_text
            },
            user_id=settings.current_user_id,
            role_id=role_id
        )
    except Exception:
        pass

    # Fallback：若 persona graph 失敗，用簡短自然問候（[R05] 短、像真人）
    if not greeting_text:
        name = expert_row["name"]
        greeting_text = f"嗨，我是{name}。想先聽聽看你這邊的狀況？"

    # 落地 chat_transcripts（L1，本地 SQLite）
    greeting_id = str(_uuid.uuid4())
    try:
        await _db_adapter.execute(
            "INSERT INTO chat_transcripts (id, thread_id, persona_id, role, content, role_id) "
            "VALUES (:id, :tid, :pid, 'assistant', :content, :rid)",
            {
                "id": greeting_id,
                "tid": thread_id,
                "pid": persona_id,
                "content": greeting_text,
                "rid": str(role_uuid),
            },
        )
    except Exception as e:
        logger.error("[confirm_match] Failed to save greeting to chat_transcripts: %s", e)

    try:
        from m0_4_logging.writer import get_logger as get_log_writer
        await get_log_writer().emit_execution_log(
            module="M4.1",
            action="confirm_match_success",
            level="INFO",
            message=f"Match confirmation completed for expert {expert_row['name']}",
            payload={
                "persona_id": persona_id,
                "thread_id": thread_id,
                "greeting_id": greeting_id
            },
            user_id=settings.current_user_id,
            role_id=role_id
        )
    except Exception:
        pass

    return {
        "persona_id": persona_id,
        "thread_id": thread_id,
        "greeting_message": greeting_text,
        "expert_name": expert_row["name"],
    }


@app.delete("/api/m4_1/experts/{expert_id}")
async def m4_1_delete_expert(expert_id: str, request: Request) -> dict[str, Any]:
    """
    [GAP-A4][RISK-17] 刪除 AI 專家。
    若刪除後角色的專家池清空，廣播 EXPERT_POOL_EMPTY SSE 事件。
    """
    role_id = request.query_params.get("role_id", "")
    if not role_id:
        raise HTTPException(status_code=422, detail="role_id query param is required")

    # 確認專家存在且屬於此角色
    expert_row = await _db_adapter.fetch_one(
        "SELECT id FROM ai_experts WHERE id = :eid AND role_id = :rid AND is_active = 1",
        {"eid": expert_id, "rid": role_id}
    )
    if not expert_row:
        raise HTTPException(status_code=404, detail="Expert not found for this role")

    # 軟刪除（is_active = 0）以保留歷史 chat_transcripts 完整性
    await _db_adapter.execute(
        "UPDATE ai_experts SET is_active = 0 WHERE id = :eid",
        {"eid": expert_id}
    )
    logger.info("[GAP-A4] Expert deactivated: %s (role=%s)", expert_id, role_id)

    # [RISK-17] 檢查是否清空了專家池
    remaining = await _db_adapter.fetch_one(
        "SELECT COUNT(*) as cnt FROM ai_experts WHERE role_id = :rid AND is_active = 1",
        {"rid": role_id}
    )
    remaining_count = (remaining or {}).get("cnt", 1)
    if remaining_count == 0:
        await _sse_broadcast({
            "type": "EXPERT_POOL_EMPTY",
            "role_id": role_id,
        })
        logger.warning("[RISK-17] Expert pool is now empty for role=%s", role_id)

    return {"status": "deleted", "expert_id": expert_id, "pool_empty": remaining_count == 0}


@app.patch("/api/m4_6/projects/{project_id}")
async def m4_6_update_project(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
    """
    [GAP/測試回饋] 編輯專案標籤（改名/描述）。供前端 system event hint 與 Project board 使用。
    [RISK-06] 以 role_id 驗證所有權。
    """
    role_id = body.get("role_id", "") or request.query_params.get("role_id", "")
    new_name = body.get("name")
    new_desc = body.get("description")
    if not role_id:
        raise HTTPException(status_code=422, detail="role_id is required")

    proj = await _db_adapter.fetch_one(
        "SELECT id FROM role_projects WHERE id = :pid AND role_id = :rid",
        {"pid": project_id, "rid": role_id}
    )
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found for this role")

    if new_name is not None:
        await _db_adapter.execute(
            "UPDATE role_projects SET name = :name WHERE id = :pid",
            {"name": new_name, "pid": project_id}
        )
    if new_desc is not None:
        await _db_adapter.execute(
            "UPDATE role_projects SET description = :desc WHERE id = :pid",
            {"desc": new_desc, "pid": project_id}
        )
    return {"status": "updated", "project_id": project_id}


@app.delete("/api/m4_6/projects/{project_id}")
async def m4_6_delete_project(project_id: str, request: Request) -> dict[str, Any]:
    """
    [測試回饋] 刪除（封存）專案標籤。軟刪除 status='archived' 保留歷史。
    [RISK-06] 以 role_id 驗證所有權。
    """
    role_id = request.query_params.get("role_id", "")
    if not role_id:
        raise HTTPException(status_code=422, detail="role_id query param is required")

    proj = await _db_adapter.fetch_one(
        "SELECT id FROM role_projects WHERE id = :pid AND role_id = :rid",
        {"pid": project_id, "rid": role_id}
    )
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found for this role")

    await _db_adapter.execute(
        "UPDATE role_projects SET status = 'archived' WHERE id = :pid",
        {"pid": project_id}
    )
    logger.info("[M4.6] Project tag archived: %s (role=%s)", project_id, role_id)
    return {"status": "archived", "project_id": project_id}


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
    user_id = get_safe_user_id(request)
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
    google_token = body.get("token")  # noqa: F841
    user_id = get_safe_user_id(request)
    
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
    """Observer 背景萃取事件 SSE 通道 — 廣播真實 PROJECT_CREATED / GOAL_INFERRED 事件"""
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _sse_subscribers.append(client_queue)

    async def generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except TimeoutError:
                    # keepalive ping
                    yield f"data: {json.dumps({'type': 'PING'})}\n\n"
        finally:
            try:
                _sse_subscribers.remove(client_queue)
            except ValueError:
                pass

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
