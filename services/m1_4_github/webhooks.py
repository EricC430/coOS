"""
M1.4.2 -- GitHub Webhook Router

SPEC: docs/modules/M1_4_git_workflow_telemetry_SPEC.md §7.2
Research: [R06: 版本控制紀錄 §2.1] commit/PR 事件作為認知狀態感測器
"""
from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request

from config import get_settings

from .schema import CommitInfo, GitActivityPayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks")


def _verify_signature(body: bytes, signature: str) -> bool:
    """[M1.4.2] HMAC-SHA256 Webhook signature verification."""
    settings = get_settings()
    secret = settings.github_webhook_secret
    if not secret:
        logger.warning("[M1.4.2] GITHUB_WEBHOOK_SECRET not set in config — rejecting all webhooks")
        return False
    logger.debug("[M1.4.2] Verifying signature with secret length: %d", len(secret))
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


async def emit_log(*, module: str, action: str, payload: dict) -> None:
    """Write GitActivityEvent to raw_tracking_logs via M0.4 pipeline.

    [R06: 版本控制紀錄 §2.1] commit history as cognitive state sensor.
    Thin wrapper kept separate so tests can mock it cleanly.
    """
    from m0_4_logging.writer import get_logger
    log_writer = get_logger()
    await log_writer.emit(module=module, action=action, level="INFO", payload=payload)


def _parse_push(payload: dict) -> GitActivityPayload:
    """[R06 §2.1] Extract structured fields from GitHub push payload."""
    repo_name = payload.get("repository", {}).get("name", "unknown")
    commits_raw = payload.get("commits", [])

    # Collect all touched files (relative paths only — never absolute)
    all_files: set[str] = set()
    commits: list[CommitInfo] = []
    for c in commits_raw:
        for key in ("added", "removed", "modified"):
            for f in c.get(key, []):
                # Strip any absolute path prefix — keep relative only
                relative = f.lstrip("/").lstrip("\\")
                all_files.add(relative)
        commits.append(CommitInfo(
            hash=c.get("id", "")[:12],
            message=c.get("message", ""),
            timestamp=c.get("timestamp", ""),
        ))

    return GitActivityPayload(
        repo_name=repo_name,
        commit_count=len(commits_raw),
        files_changed=len(all_files),
        files=sorted(all_files),
        commits=commits,
    )


def _parse_pr(payload: dict) -> GitActivityPayload:
    """[R06 §2.1] Extract structured fields from GitHub PR payload."""
    repo_name = payload.get("repository", {}).get("name", "unknown")
    pr = payload.get("pull_request", {})
    return GitActivityPayload(
        repo_name=repo_name,
        changed_files=pr.get("changed_files", 0),
        pr_number=pr.get("number"),
    )


@router.post("/github")
async def github_webhook(request: Request):
    """[M1.4.2] Receive GitHub Webhook events forwarded by gh webhook forward.

    Verifies HMAC-SHA256 signature, parses push/PR payloads, writes to
    raw_tracking_logs (L1 — never leaves local storage).
    """
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not _verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    if event_type == "push":
        activity = _parse_push(payload)
        await emit_log(module="M1.4.2", action="commit_push", payload=activity.model_dump())
        return {"status": "ok", "action": "commit_push"}

    elif event_type == "pull_request":
        pr_action = payload.get("action", "opened")
        mapped = "pr_opened" if pr_action == "opened" else "pr_closed"
        activity = _parse_pr(payload)
        await emit_log(module="M1.4.2", action=mapped, payload=activity.model_dump())
        return {"status": "ok", "action": mapped}

    else:
        # Unknown event — accept but do not process
        logger.debug("[M1.4.2] Unhandled GitHub event type: %s", event_type)
        from fastapi.responses import Response
        return Response(status_code=204)
