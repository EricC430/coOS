from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 0: minimal startup — config validation added in M0.3
    yield


app = FastAPI(title="coOS Sidecar", version="0.1.0", lifespan=lifespan)

# [架構文件 §7] 僅允許 Tauri 與本地開發 origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_start_time = time.time()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - _start_time),
    }
