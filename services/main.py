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
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings
from m0_4_logging.schema import LogEvent
from m1_2_breakpoint.breakpoint_engine import BreakpointEngine
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

logger = logging.getLogger(__name__)
_start_time = time.time()

# --- module singletons (initialized in lifespan) ---
_debouncer: EventDebouncer | None = None
_gemma_pipeline: GemmaInferencePipeline | None = None
_eguard_filter: EguardFilter | None = None
_drift_shield: DriftShield | None = None
_breakpoint_engine: BreakpointEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """[M0_3 SPEC §7.4] 啟動時驗證設定，關閉時清理連線"""
    settings = get_settings()

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
        # In MVP, batches are stored in intent_logs via compress() calls
        # Full pipeline integration is Phase 3+ (M4.1 router)
        logger.info("[M2.1] batch flushed: size=%d role=%s", batch.size, batch.role_id)

    _debouncer = EventDebouncer(
        role_id="default",
        flush_fn=_m2_2_flush,
        db_path=str(settings.local_db_path),
    )
    _eguard_filter = EguardFilter()
    _drift_shield = DriftShield(ai_local_host=settings.ai_local_host)

    logger.info("[M0.3] coOS sidecar 啟動完成 (local_only=%s)", not settings.gemini_api_key)
    yield
    if _debouncer:
        await _debouncer.shutdown_gracefully()
    from m0_4_logging.writer import get_logger as get_log_writer
    await get_log_writer().stop()
    logger.info("[M0.3] coOS sidecar 關閉")


app = FastAPI(title="coOS Sidecar", version="0.1.0", lifespan=lifespan)

# [架構文件 §7] 僅允許 Tauri 與本地開發 origin
# [M0_2 SPEC §7.4] FastAPI sidecar 必須綁定 127.0.0.1，CSP 設定於 tauri.conf.json
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    )
    # [M1.2 SPEC §3] Forward to BreakpointEngine — M1.1 events are M1.2's primary input
    engine = _get_breakpoint_engine()
    await engine.feed({
        "module": event.module,
        "action": event.action,
        "payload": event.payload,
    })
    return {"status": "ok", "event_id": event.id}


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

# --- M6.3 Role Context ---

@app.get("/api/m6_3/role_context")
async def m6_3_role_context(role_id: str) -> dict[str, Any]:
    """Context Header 四槽位資料 (Project / Role / Promises / Goal)"""
    # Seed data — replaced by real DB query when M6.3 migration is run
    return {
        "role_id": role_id,
        "project": {"name": "期末考準備"},
        "role": {"name": role_id.split("_")[0].upper()},
        "promises": ["每天寫 1 小時程式", "本週完成微積分作業"],
        "goals": ["通過資料結構期末考"],
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
    return {"id": reflection_id, "status": "updated", **body}


# --- M4.5 XP Settlement ---

@app.patch("/api/m4_5/grant_xp")
async def m4_5_grant_xp(body: dict[str, Any]) -> dict[str, Any]:
    """[RISK-01] 只在 is_reviewed=true 後呼叫；回傳發放金額"""
    if not body.get("is_reviewed"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="RISK-01: is_reviewed must be true")
    xp_amount = 50  # Base XP; real calculation in M4.5 engine
    logger.info("[M4.5] XP granted: reflection_id=%s amount=%d", body.get("reflection_id"), xp_amount)
    return {"granted": True, "amount": xp_amount}


# --- M6.5 Achievements ---

@app.get("/api/m6_5/user_collections")
async def m6_5_user_collections() -> list[dict[str, Any]]:
    return [
        {"id": "badge_001", "name": "首次反思", "rarity": "common",
         "description": "完成第一次反思草稿核准", "acquired_at": "2026-06-01",
         "unlock_condition": "核准第一份日報草稿"},
        {"id": "badge_002", "name": "CPE 挑戰者", "rarity": "rare",
         "description": "報名 CPE 程式能力檢定", "acquired_at": "2026-05-20",
         "unlock_condition": "在 CSIE 角色記錄 CPE 準備 Project"},
    ]


@app.get("/api/m6_5/items_dictionary")
async def m6_5_items_dictionary() -> list[dict[str, Any]]:
    return [
        {"id": "badge_001", "name": "首次反思", "rarity": "common"},
        {"id": "badge_002", "name": "CPE 挑戰者", "rarity": "rare"},
        {"id": "badge_003", "name": "連續 7 天", "rarity": "epic"},
        {"id": "badge_004", "name": "學期之星", "rarity": "legendary"},
    ]


# --- M4.1 Chat (LangGraph) ---

@app.post("/api/m4_1/chat")
async def m4_1_chat(body: dict[str, Any]) -> dict[str, Any]:
    """對話端點 — Phase 5 seed response; 接上 LangGraph 後換真實推論"""
    user_msg = body.get("content", "")
    role_id = body.get("role_id", "")
    persona_greetings = {
        "csie_001": "學長在這！關於你說的問題，我們來一步一步拆解...",
        "family_001": "嗨～有什麼心事想聊聊嗎？",
    }
    reply = persona_greetings.get(role_id, f"我收到了你的訊息：「{user_msg[:30]}」，讓我想想...")
    return {"content": reply, "persona_id": "robert_001", "thread_id": body.get("thread_id")}


@app.post("/api/m4_1/match_persona")
async def m4_1_match_persona(body: dict[str, Any]) -> dict[str, Any]:
    """配對最合適的 Persona"""
    return {"persona_id": "robert_001", "matched": True, "reason": "rule_match"}


# --- M4.6 Observer SSE ---

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

@app.get("/api/m1_4/connected_sources")
async def m1_4_connected_sources() -> list[dict[str, Any]]:
    return []


@app.post("/api/m1_4/bind_source")
async def m1_4_bind_source(body: dict[str, Any]) -> dict[str, Any]:
    return {"status": "connected", "source_type": body.get("source_type")}


@app.post("/api/m1_4/create_trigger")
async def m1_4_create_trigger(body: dict[str, Any]) -> dict[str, Any]:
    return {"id": "trigger_001", "status": "created", **body}
