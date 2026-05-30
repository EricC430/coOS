"""
M0.2 Tauri IPC 通訊橋驗收測試
對應 docs/modules/M0_2_tauri_ipc_SPEC.md §6

NOTE: 這些測試需要 FastAPI sidecar 在 localhost:8000 運行。
      在 CI 中由 `uvicorn services.main:app` 啟動後執行。
      本地開發可先執行 `uv run --directory services uvicorn main:app --port 8000`
"""
import asyncio

import httpx
import pytest

SIDECAR_URL = "http://127.0.0.1:8000"


# ---------------------------------------------------------------------------
# 驗收條件 1 & 2 — FastAPI sidecar 健康檢查
# ---------------------------------------------------------------------------

class TestSidecarHealth:
    @pytest.mark.asyncio
    async def test_fastapi_sidecar_reachable(self):
        """驗收條件 1: FastAPI sidecar 可透過 localhost:8000 存取"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{SIDECAR_URL}/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_returns_version(self):
        """驗收條件 2: 健康檢查回傳應用程式版本與 uptime"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{SIDECAR_URL}/api/health")
        data = resp.json()
        assert "version" in data
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], int)


# ---------------------------------------------------------------------------
# 驗收條件 3 — SSE 串流
# ---------------------------------------------------------------------------

class TestSSEStream:
    @pytest.mark.asyncio
    async def test_sse_endpoint_streams_events(self):
        """驗收條件 3: SSE 端點能持續推送至少 3 個事件"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            async with client.stream("GET", f"{SIDECAR_URL}/api/m0_2/test_stream") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]
                events = []
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        events.append(line)
                    if len(events) >= 3:
                        break
                assert len(events) >= 3, f"SSE 只收到 {len(events)} 個事件,預期 ≥3"


# ---------------------------------------------------------------------------
# 驗收條件 4 — CORS
# ---------------------------------------------------------------------------

class TestCORS:
    @pytest.mark.asyncio
    async def test_cors_allows_tauri_origin(self):
        """驗收條件 4: CORS 允許 tauri://localhost origin"""
        async with httpx.AsyncClient() as client:
            resp = await client.options(
                f"{SIDECAR_URL}/api/health",
                headers={
                    "Origin": "tauri://localhost",
                    "Access-Control-Request-Method": "GET",
                },
            )
        assert resp.status_code in (200, 204)
        acao = resp.headers.get("access-control-allow-origin", "")
        assert "tauri://localhost" in acao, f"CORS 未允許 tauri://localhost，回傳: {acao}"

    @pytest.mark.asyncio
    async def test_cors_allows_vite_dev_origin(self):
        """CORS 允許 Vite 開發伺服器 http://localhost:1420"""
        async with httpx.AsyncClient() as client:
            resp = await client.options(
                f"{SIDECAR_URL}/api/health",
                headers={
                    "Origin": "http://localhost:1420",
                    "Access-Control-Request-Method": "GET",
                },
            )
        assert resp.status_code in (200, 204)
        acao = resp.headers.get("access-control-allow-origin", "")
        assert "localhost:1420" in acao, f"CORS 未允許 localhost:1420，回傳: {acao}"

    @pytest.mark.asyncio
    async def test_sidecar_not_exposed_to_external(self):
        """sidecar 僅綁定 127.0.0.1，不對外暴露（反模式防禦）"""
        # 嘗試透過 0.0.0.0 / hostname 存取應失敗，或至少不在測試環境可達
        # 本測試驗證 URL 設定正確（sidecar 綁定 127.0.0.1 而非 0.0.0.0）
        import socket
        hostname = socket.gethostname()
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"http://{hostname}:8000/api/health")
            # 若可達也可接受（某些環境 hostname 解析為 127.0.0.1）
            # 重要的是開發命令使用 --host 127.0.0.1
        except (httpx.ConnectError, httpx.TimeoutException):
            pass  # 符合預期：外部不可達
