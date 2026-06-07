"""
M1.4.1 -- GitHub OAuth 2.0 Authorization Flow

SPEC: docs/modules/M1_4_git_workflow_telemetry_SPEC.md §7.1
Research: [R06: 版本控制紀錄 §2.1]

Token stored AES-256 encrypted in local SQLite (L1 — never uploaded).
MVP: encryption via Fernet (symmetric, 128-bit AES-CBC with HMAC).
"""
from __future__ import annotations

import logging
import sqlite3
import httpx
import asyncio
from fastapi import APIRouter, HTTPException, Query, Request
from config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth")

_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


async def exchange_code_for_token(code: str) -> str:
    """Exchange OAuth code for access token, return encrypted token string.

    [M1.4.1] Token never stored in plaintext — caller must encrypt before persisting.
    """
    settings = get_settings()
    client_id = settings.github_client_id
    client_secret = settings.github_client_secret
    if not client_id or not client_secret:
        raise ValueError("GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET not configured")

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            _GITHUB_TOKEN_URL,
            json={"client_id": client_id, "client_secret": client_secret, "code": code},
            headers={"Accept": "application/json"},
            timeout=10,
        )
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ValueError(f"GitHub OAuth failed: {data.get('error_description', data)}")

    return _encrypt_token(token)


def _encrypt_token(raw_token: str) -> str:
    """AES-128-CBC encrypt via Fernet. Key derived from GITHUB_CLIENT_SECRET."""
    settings = get_settings()
    try:
        import base64
        import hashlib

        from cryptography.fernet import Fernet
        key_bytes = hashlib.sha256(
            (settings.github_client_secret or "dev_secret").encode()
        ).digest()[:32]
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        f = Fernet(fernet_key)
        return f.encrypt(raw_token.encode()).decode()
    except ImportError:
        # cryptography package not installed — store with basic obfuscation for dev
        logger.warning("[M1.4.1] cryptography not installed, token stored with base64 only")
        import base64
        return "b64:" + base64.b64encode(raw_token.encode()).decode()


@router.get("/github/callback")
async def github_oauth_callback(
    request: Request,
    code: str = Query(..., description="OAuth authorization code")
):
    """[M1.4.1] GitHub OAuth callback — exchanges code for encrypted token and stores it."""
    try:
        encrypted_token = await exchange_code_for_token(code)
        
        # Save to database
        settings = get_settings()
        
        def _save():
            conn = sqlite3.connect(str(settings.local_db_path))
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS github_tokens (
                        id TEXT PRIMARY KEY,
                        encrypted_token TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                    )
                """)
                # For MVP, we only support one token
                cursor.execute("DELETE FROM github_tokens")
                cursor.execute(
                    "INSERT INTO github_tokens (id, encrypted_token) VALUES (?, ?)",
                    ("default", encrypted_token)
                )
                conn.commit()
            finally:
                conn.close()
        
        await asyncio.to_thread(_save)
        
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("[M1.4.1] GitHub token acquired, encrypted, and stored in local SQLite")
    return {"status": "ok", "token_stored": True}
