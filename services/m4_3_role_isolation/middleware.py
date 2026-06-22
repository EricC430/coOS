"""
M4.3.1 -- 沙盒中介軟體 (Role Isolation Middleware)

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §7.1
Research: [R03 §6 + RISK-06] 角色隔離中介軟體
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 不需要角色隔離的端點白名單
# [RISK-06] /api/m4_1/history, /threads, /match_persona 已移出豁免清單：
#   這三個端點均帶有 role_id query param，中介軟體 query_params 路徑可正常提取驗證。
EXEMPT_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/m6_2/roles",
    "/api/m4_6/events",
    "/api/m6_5/user_collections",
    "/api/m6_5/items_dictionary",
    "/api/m4_4/time_spent",
    "/api/m4_4/trigger_draft_cron",
    "/api/m1_1/telemetry_estimate",
    # 日報頁面是全域視圖（跨角色），不應被 role_id 過濾攔截
    "/api/m6_4/daily_timeline",
    "/api/m6_4/heatmap",
    # 社群頁面是全域融合，不應被 role_id 隔離限制
    "/api/m6_6",
}


class RoleIsolationMiddleware(BaseHTTPMiddleware):
    """
    [R03 §6] 攔截所有 /api/m4_* 與 /api/m6_* 請求，
    從 X-Role-ID header 提取角色並注入 request.state。

    缺少 X-Role-ID → 422。
    role_id 不屬於當前使用者 → 403。
    """

    def __init__(self, app, owned_roles: set[str] | None = None) -> None:
        super().__init__(app)
        # owned_roles: 測試時注入；production 從 DB 查詢
        self._owned_roles = owned_roles

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in EXEMPT_PATHS or any(path.startswith(p + "/") for p in EXEMPT_PATHS):
            return await call_next(request)

        # 只安全攔截 /api/m4_* 與 /api/m6_* 路徑
        path = request.url.path
        if not (path.startswith("/api/m4_") or path.startswith("/api/m6_")):
            return await call_next(request)

        role_id = request.headers.get("X-Role-ID")

        # 1. 嘗試從 query parameters 獲取 (支援 role_id 與 current_role_id)
        if not role_id:
            role_id = request.query_params.get("role_id") or request.query_params.get("current_role_id")

        # 2. 嘗試從 JSON body 獲取 (支援 role_id 與 current_role_id，不破壞後續處理器的讀取)
        if not role_id and request.method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                import json
                body_json = json.loads(body_bytes)
                role_id = body_json.get("role_id") or body_json.get("current_role_id")
                
                # 重設 receive 管道以便後續的路由處理器能正常讀取 Body
                async def receive():
                    return {"type": "http.request", "body": body_bytes, "more_body": False}
                request._receive = receive
            except Exception:
                pass

        if not role_id:
            try:
                from m0_4_logging.writer import get_logger as get_log_writer
                log_writer = get_log_writer()
                import asyncio
                asyncio.create_task(log_writer.emit_execution_log(
                    module="M4.3",
                    action="role_isolation_rejected",
                    level="WARNING",
                    message="Missing X-Role-ID header, role_id, or current_role_id parameter",
                    payload={"path": path, "method": request.method}
                ))
            except Exception:
                pass

            return Response(
                content='{"detail": "Missing X-Role-ID header or role_id parameter"}',
                status_code=422,
                media_type="application/json",
            )

        # 驗證 role_id 屬於當前使用者
        if self._owned_roles is not None:
            # 測試模式：使用注入的白名單
            if role_id not in self._owned_roles:
                try:
                    from m0_4_logging.writer import get_logger as get_log_writer
                    log_writer = get_log_writer()
                    import asyncio
                    asyncio.create_task(log_writer.emit_execution_log(
                        module="M4.3",
                        action="role_isolation_forbidden",
                        level="ERROR",
                        message="Role does not belong to current user (test mode)",
                        payload={"path": path, "method": request.method, "role_id": role_id}
                    ))
                except Exception:
                    pass

                return Response(
                    content='{"detail": "Role does not belong to current user"}',
                    status_code=403,
                    media_type="application/json",
                )
        else:
            # Production 模式：從 DB 查詢（需要 auth middleware 先設定 user_id）
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                valid = await _validate_role_ownership(user_id, role_id)
                if not valid:
                    try:
                        from m0_4_logging.writer import get_logger as get_log_writer
                        log_writer = get_log_writer()
                        import asyncio
                        asyncio.create_task(log_writer.emit_execution_log(
                            module="M4.3",
                            action="role_isolation_forbidden",
                            level="ERROR",
                            message="Role does not belong to current user",
                            payload={"path": path, "method": request.method, "role_id": role_id},
                            user_id=user_id
                        ))
                    except Exception:
                        pass

                    return Response(
                        content='{"detail": "Role does not belong to current user"}',
                        status_code=403,
                        media_type="application/json",
                    )

        request.state.role_id = role_id
        return await call_next(request)


async def _validate_role_ownership(user_id: str, role_id: str) -> bool:
    """Production 用：從 DB 驗證 role 屬於 user。"""
    try:
        import main as _main
        _db_adapter = getattr(_main, "_db_adapter", None)
    except Exception:
        _db_adapter = None
    if not _db_adapter:
        return True # Fallback for early startup
        
    try:
        # role_id can be UUID string or slug
        query = "SELECT id FROM roles WHERE user_id = :uid AND (id = :rid OR slug = :rid)"
        row = await _db_adapter.fetch_one(query, {"uid": user_id, "rid": role_id})
        return row is not None
    except Exception as e:
        logger.error("[M4.3] Role ownership validation error: %s", e)
        return False


def create_test_app(owned_roles: set[str] | None = None) -> FastAPI:
    """
    建立帶有 RoleIsolationMiddleware 的測試用 FastAPI app。
    owned_roles: 允許通過驗證的 role_id 集合（None = 不驗證擁有權）。
    """
    app = FastAPI()
    app.add_middleware(RoleIsolationMiddleware, owned_roles=owned_roles)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/m4_1/chat")
    async def chat(request: Request):
        return {"role_id": request.state.role_id}

    return app
