"""
coOS FastAPI Sidecar — 主入口

實作 SPEC: docs/modules/M0_2_tauri_ipc_SPEC.md (IPC 橋)
         docs/modules/M0_3_env_alembic_SPEC.md (啟動驗證)
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import get_settings

logger = logging.getLogger(__name__)
_start_time = time.time()


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

    logger.info("[M0.3] coOS sidecar 啟動完成 (local_only=%s)", not settings.gemini_api_key)
    yield
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
