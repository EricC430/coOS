"""
M1.2.2 -- Deep Work Guard

SPEC: docs/modules/M1_2_breakpoint_detection_SPEC.md §7.1 M1.2.2
Research: [R08: §一 認知負荷轉移] High-load interruption cost justifies system mute.

Sends set_notification_mode IPC command to Tauri on DEEP_WORK entry/exit.
Tauri Rust side calls Win32 SetNotificationMode (Focus Assist API).
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_TAURI_IPC_URL = "http://127.0.0.1:8000/api/tauri/command"


async def send_tauri_command(command: dict) -> None:
    """Send a command to Tauri via FastAPI IPC bridge.

    [M1.2 SPEC §7 架構] Python side sends JSON command; Tauri Rust executes Win32 call.
    Fire-and-forget: log failure but never block the breakpoint engine.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(_TAURI_IPC_URL, json=command)
    except Exception as exc:
        logger.warning("[M1.2.2] Tauri command failed (non-blocking): %s", exc)


async def enter_deep_work() -> None:
    """[R08 §一] Mute system notifications on DEEP_WORK entry."""
    await send_tauri_command({"command": "set_notification_mode", "mode": "mute"})
    logger.info("[M1.2.2] System notifications muted (DEEP_WORK entered)")


async def exit_deep_work() -> None:
    """[R08 §一] Restore system notifications on DEEP_WORK exit."""
    await send_tauri_command({"command": "set_notification_mode", "mode": "restore"})
    logger.info("[M1.2.2] System notifications restored (DEEP_WORK exited)")
