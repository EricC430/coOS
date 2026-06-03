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
EXEMPT_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/m6_2/roles",
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
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # 只攔截 /api/ 路徑
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        role_id = request.headers.get("X-Role-ID")
        if not role_id:
            return Response(
                content='{"detail": "Missing X-Role-ID header"}',
                status_code=422,
                media_type="application/json",
            )

        # 驗證 role_id 屬於當前使用者
        if self._owned_roles is not None:
            # 測試模式：使用注入的白名單
            if role_id not in self._owned_roles:
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
                    return Response(
                        content='{"detail": "Role does not belong to current user"}',
                        status_code=403,
                        media_type="application/json",
                    )

        request.state.role_id = role_id
        return await call_next(request)


async def _validate_role_ownership(user_id: str, role_id: str) -> bool:
    """Production 用：從 DB 驗證 role 屬於 user（MVP 階段直接回 True，等 M3.1 auth 接入）。"""
    return True


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
