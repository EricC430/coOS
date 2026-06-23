"""
M4.4 -- Gibbs Reflection Structure Template

SPEC: docs/modules/M4_4_natural_elicitation_draft_SPEC.md SS7.4
[R08 SS6.2] Gibbs Cycle phases 1-2 filled by AI; phases 3-5 left for user (micro-friction).
[R10 SSMindScape] Reflection scaffolding must be specific enough to trigger memory retrieval.

Privacy constraints (RISK-15):
  - content_summary is L1 data -- can only go to local Gemma edge LLM, NEVER to cloud LLM.
  - Cloud LLM (Gemini Flash) receives only: app_bucket, duration_s, wpm_avg,
    activity_state, new_state, breakpoint type/confidence.
  - If both LLMs unavailable, structured template fallback always produces real values --
    never "unknown" or "0 minutes".

LLM call contract:
  - Primary: local Gemma (http://ai.local) -- receives full signal set including content_summary
  - Fallback: Gemini Flash -- receives privacy-safe subset only (no content_summary)
  - Retry: each endpoint tried once; no infinite loops.
  - On total failure: return deterministic structured description + log WARNING.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App bucket display labels (serde snake_case from Rust AppBucket enum)
# ---------------------------------------------------------------------------

_BUCKET_LABEL: dict[str, str] = {
    "coding":          "程式開發",
    "writing":         "寫作創作",
    "reading":         "閱讀研究",
    "communication":   "溝通協作",
    "productivity":    "生產力工具",
    "idle":            "待機",
    "unknown":         "其他應用",
}

_STATE_LABEL: dict[str, str] = {
    "DEEP_FOCUS":          "深度專注",
    "ACTIVE":              "主動作業",
    "PASSIVE_CONSUMPTION": "被動接收",
    "DOOM_SCROLLING":      "無意識滑動",
    "CONTEXT_SWITCHING":   "頻繁切換",
    "RESEARCH_READING":    "研究閱讀",
    "MEETING_CALL":        "會議通話",
    "IDLE":                "閒置",
}

_BREAKPOINT_LABEL: dict[str, str] = {
    "app_switch":      "應用切換",
    "idle_timeout":    "閒置逾時",
    "wpm_drop":        "輸入速率驟降",
    "ide_focus_leave": "離開開發環境",
    "doom_scrolling":  "偵測到無意識滑動",
}

# ---------------------------------------------------------------------------
# App-name friendly labels (M1.1 emits raw exe names; app_bucket is often "unknown")
# When app_bucket is unknown but app_name is present, we surface the program name
# instead of the useless "其他應用" bucket label.
# ---------------------------------------------------------------------------

_APP_NAME_LABEL: dict[str, str] = {
    "antigravity.exe":     "Antigravity IDE",
    "antigravity ide.exe": "Antigravity IDE",
    "code.exe":            "VS Code",
    "msedge.exe":          "Microsoft Edge",
    "msedgewebview2.exe":  "Microsoft Edge",
    "chrome.exe":          "Chrome",
    "firefox.exe":         "Firefox",
    "coos-desktop.exe":    "coOS 桌面程式",
    "explorer.exe":        "檔案總管",
    "db browser for sqlite.exe": "DB Browser",
    "code - insiders.exe": "VS Code Insiders",
    "windowsterminal.exe": "終端機",
    "powershell.exe":      "PowerShell",
    "pwsh.exe":            "PowerShell",
    "notion.exe":          "Notion",
    "slack.exe":           "Slack",
    "discord.exe":         "Discord",
    "obsidian.exe":        "Obsidian",
    "acrobat.exe":         "PDF 閱讀",
    "acrord32.exe":        "PDF 閱讀",
    "winword.exe":         "Word",
    "excel.exe":           "Excel",
    "powerpnt.exe":        "PowerPoint",
}


def friendly_app_name(app_name: str) -> str:
    """Map a raw exe name to a human-readable label; strip .exe as a last resort."""
    if not app_name:
        return ""
    key = app_name.strip().lower()
    if key in _APP_NAME_LABEL:
        return _APP_NAME_LABEL[key]
    # Fallback: strip .exe and title-case the stem
    stem = app_name.strip()
    if stem.lower().endswith(".exe"):
        stem = stem[:-4]
    return stem

# ---------------------------------------------------------------------------
# Typed signal grouping
# ---------------------------------------------------------------------------

@dataclass
class DaySignals:
    """Grouped signals for one focus session."""
    # From focus_session_ended
    app_bucket: str = "unknown"
    app_name: str = ""
    duration_s: int = 0
    wpm_avg: float = 0.0
    activity_state: str = ""
    end_timestamp_iso: str = ""

    # From content_capture (L1, local-LLM only -- RISK-15)
    content_summaries: list[str] = field(default_factory=list)

    # From activity_state_changed
    state_transitions: list[str] = field(default_factory=list)

    # From breakpoint_detected
    breakpoint_types: list[str] = field(default_factory=list)
    breakpoint_confidences: list[float] = field(default_factory=list)

    @property
    def duration_minutes(self) -> float:
        return self.duration_s / 60.0

    @property
    def bucket_label(self) -> str:
        # Prefer friendly app name when bucket is unknown/empty -- never show "其他應用"
        # if we actually know the program the user was in.
        if self.app_bucket and self.app_bucket != "unknown":
            return _BUCKET_LABEL.get(self.app_bucket, self.app_bucket)
        if self.app_name:
            return friendly_app_name(self.app_name)
        return _BUCKET_LABEL.get(self.app_bucket, "其他應用")

    @property
    def state_label(self) -> str:
        return _STATE_LABEL.get(self.activity_state, self.activity_state or "")


def group_signals(logs: list) -> list[DaySignals]:
    """
    Consume raw_tracking_logs records (SimpleNamespace with .action/.payload/.timestamp)
    and return one DaySignals per focus_session_ended event, enriched with
    content_capture / activity_state_changed / breakpoint_detected events that
    are adjacent (before next focus_session_ended).

    If there are no focus_session_ended events, returns supplementary signals as
    a single orphan DaySignals so at least something is visible.
    """
    focus_sessions: list[DaySignals] = []
    orphan = DaySignals()

    def _action(log: Any) -> str:
        if isinstance(log, dict):
            return log.get("action", "")
        return getattr(log, "action", "")

    def _payload(log: Any) -> dict:
        if isinstance(log, dict):
            return log.get("payload", log)
        return getattr(log, "payload", {}) or {}

    def _ts(log: Any) -> str:
        if isinstance(log, dict):
            return log.get("timestamp", "")
        return getattr(log, "timestamp", "") or ""

    for log in logs:
        action = _action(log)
        p = _payload(log)

        if action == "focus_session_ended":
            sig = DaySignals(
                app_bucket=str(p.get("app_bucket", "unknown")),
                app_name=str(p.get("app_name", "")),
                duration_s=int(p.get("duration_s", 0)),
                wpm_avg=float(p.get("wpm_avg", 0.0)),
                activity_state=str(p.get("activity_state", "")),
                end_timestamp_iso=_ts(log),
            )
            focus_sessions.append(sig)

        elif action == "content_capture":
            summary = p.get("content_summary", "")
            cc_app = str(p.get("app_name", "")).lower()
            # Route summary to the nearest session with the SAME app_name (working
            # backwards from the end). This prevents VS Code summaries from leaking
            # into an Edge session or vice versa when the user switches quickly.
            target = None
            if cc_app and focus_sessions:
                for fs in reversed(focus_sessions):
                    if fs.app_name.lower() == cc_app:
                        target = fs
                        break
            if target is None:
                target = focus_sessions[-1] if focus_sessions else orphan
            if summary:
                target.content_summaries.append(str(summary))
            # Backfill app_name when the focus session lacked it
            if cc_app and not target.app_name:
                target.app_name = str(p.get("app_name", ""))

        elif action == "activity_state_changed":
            new_state = p.get("new_state", "")
            if new_state:
                target = focus_sessions[-1] if focus_sessions else orphan
                target.state_transitions.append(str(new_state))

        elif action == "breakpoint_detected":
            bp_type = p.get("type", "")
            bp_conf = float(p.get("confidence", 0.0))
            if bp_type:
                target = focus_sessions[-1] if focus_sessions else orphan
                target.breakpoint_types.append(str(bp_type))
                target.breakpoint_confidences.append(bp_conf)

    if not focus_sessions:
        has_supplementary = (
            orphan.content_summaries or orphan.state_transitions or orphan.breakpoint_types
        )
        return [orphan] if has_supplementary else []

    # Attach orphan supplementary signals to first session
    if orphan.content_summaries:
        focus_sessions[0].content_summaries = orphan.content_summaries + focus_sessions[0].content_summaries
    if orphan.state_transitions:
        focus_sessions[0].state_transitions = orphan.state_transitions + focus_sessions[0].state_transitions
    if orphan.breakpoint_types:
        focus_sessions[0].breakpoint_types = orphan.breakpoint_types + focus_sessions[0].breakpoint_types
        focus_sessions[0].breakpoint_confidences = (
            orphan.breakpoint_confidences + focus_sessions[0].breakpoint_confidences
        )
    return focus_sessions


# ---------------------------------------------------------------------------
# Semantic merging: collapse fragmented focus sessions into activity blocks
# ---------------------------------------------------------------------------

# Two adjacent sessions merge if same app AND gap below this (seconds).
_MERGE_GAP_S = 600  # 10 minutes
# Token overlap above this fraction => same topic, merge across apps too.
_MERGE_TOPIC_OVERLAP = 0.34
# Session-window pass: adjacent blocks within this gap collapse into one work session
# even across different (same-family) apps. A session never exceeds _MAX_BLOCK_S.
_SESSION_GAP_S = 300       # 5 minutes -- continuous activity
_MAX_BLOCK_S = 5400        # 90 minutes -- cap so one card never spans the whole day

# App context families. Cross-app merge within a session only happens inside one family,
# so leisure browsing never folds into a coding session.
_APP_FAMILY: dict[str, str] = {
    "antigravity.exe": "dev", "antigravity ide.exe": "dev", "code.exe": "dev",
    "code - insiders.exe": "dev", "coos-desktop.exe": "dev",
    "windowsterminal.exe": "dev", "powershell.exe": "dev", "pwsh.exe": "dev",
    "db browser for sqlite.exe": "dev", "explorer.exe": "dev",
    "msedge.exe": "web", "msedgewebview2.exe": "web", "chrome.exe": "web", "firefox.exe": "web",
    "winword.exe": "doc", "excel.exe": "doc", "powerpnt.exe": "doc",
    "acrobat.exe": "doc", "acrord32.exe": "doc", "notion.exe": "doc", "obsidian.exe": "doc",
}


def _app_family(app_name: str) -> str:
    if not app_name:
        return ""
    return _APP_FAMILY.get(app_name.strip().lower(), "")


def _summary_tokens(sig: "DaySignals") -> set[str]:
    from m4_4_elicitation.role_inference import _tokenize
    toks: set[str] = set()
    for s in sig.content_summaries:
        toks |= _tokenize(s)
    return toks


def _parse_iso(ts: str):
    if not ts:
        return None
    try:
        from datetime import datetime, timezone
        t = ts.rstrip("Z")
        if "+" in t:
            t = t[:t.index("+")]
        return datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _should_merge(prev: "DaySignals", cur: "DaySignals") -> bool:
    """Merge cur into prev if same program with small gap, or topic overlap is high."""
    same_app = bool(prev.app_name) and prev.app_name == cur.app_name
    # Time gap between prev end and cur end (we only store end timestamps; use end-to-end
    # minus cur duration as a proxy for cur start).
    prev_end = _parse_iso(prev.end_timestamp_iso)
    cur_end = _parse_iso(cur.end_timestamp_iso)
    gap_ok = True
    if prev_end and cur_end:
        cur_start = cur_end.timestamp() - cur.duration_s
        gap = cur_start - prev_end.timestamp()
        gap_ok = gap <= _MERGE_GAP_S

    if same_app and gap_ok:
        return True

    # Cross-app merge only when the topic clearly continues
    pt, ct = _summary_tokens(prev), _summary_tokens(cur)
    if pt and ct:
        overlap = pt & ct
        denom = min(len(pt), len(ct))
        if denom and len(overlap) / denom >= _MERGE_TOPIC_OVERLAP and gap_ok:
            return True
    return False


def _merge_pair(prev: "DaySignals", cur: "DaySignals") -> None:
    """Fold cur into prev in place. prev keeps the earlier identity, accumulates signals."""
    prev.duration_s += cur.duration_s
    # Keep the latest end timestamp as the block end
    pe, ce = _parse_iso(prev.end_timestamp_iso), _parse_iso(cur.end_timestamp_iso)
    if ce and (not pe or ce > pe):
        prev.end_timestamp_iso = cur.end_timestamp_iso
    # Duration-weighted WPM
    total = prev.duration_s if prev.duration_s else 1
    prev.wpm_avg = (prev.wpm_avg * (prev.duration_s - cur.duration_s) + cur.wpm_avg * cur.duration_s) / total
    # Prefer a known (non-unknown) bucket / non-idle state
    if (not prev.app_bucket or prev.app_bucket == "unknown") and cur.app_bucket and cur.app_bucket != "unknown":
        prev.app_bucket = cur.app_bucket
    if (not prev.activity_state or prev.activity_state in ("IDLE", "")) and cur.activity_state:
        prev.activity_state = cur.activity_state
    if not prev.app_name and cur.app_name:
        prev.app_name = cur.app_name
    # Accumulate de-duplicated content summaries / transitions / breakpoints
    for s in cur.content_summaries:
        if s not in prev.content_summaries:
            prev.content_summaries.append(s)
    prev.state_transitions.extend(cur.state_transitions)
    prev.breakpoint_types.extend(cur.breakpoint_types)
    prev.breakpoint_confidences.extend(cur.breakpoint_confidences)


def _session_gap_ok(prev: "DaySignals", cur: "DaySignals") -> bool:
    """True if cur starts within _SESSION_GAP_S of prev's end and block stays under cap."""
    if prev.duration_s + cur.duration_s > _MAX_BLOCK_S:
        return False
    pe, ce = _parse_iso(prev.end_timestamp_iso), _parse_iso(cur.end_timestamp_iso)
    if not pe or not ce:
        return True  # no timestamps -> assume contiguous
    cur_start = ce.timestamp() - cur.duration_s
    return (cur_start - pe.timestamp()) <= _SESSION_GAP_S


def merge_into_blocks(signals: list["DaySignals"]) -> list["DaySignals"]:
    """
    Collapse fragmented focus sessions into coherent activity blocks via two passes:

      Pass 1 (fine): merge adjacent sessions of the same program / same topic.
      Pass 2 (session): collapse remaining adjacent fragments that are close in time
              AND in the same app family (dev / web / doc) into a continuous work
              session, capped at _MAX_BLOCK_S so a card never spans the whole day.

    This turns ~110 one-minute fragments into a handful of meaningful session cards.
    """
    if not signals:
        return []
    ordered = sorted(signals, key=lambda s: s.end_timestamp_iso or "")

    # Pass 1: fine-grained same-app / same-topic merge
    pass1: list[DaySignals] = [ordered[0]]
    for cur in ordered[1:]:
        if _should_merge(pass1[-1], cur):
            _merge_pair(pass1[-1], cur)
        else:
            pass1.append(cur)

    # Pass 2: session-window merge within the same app family
    if len(pass1) <= 1:
        return pass1
    blocks: list[DaySignals] = [pass1[0]]
    for cur in pass1[1:]:
        prev = blocks[-1]
        same_family = _app_family(prev.app_name) and _app_family(prev.app_name) == _app_family(cur.app_name)
        if same_family and _session_gap_ok(prev, cur):
            _merge_pair(prev, cur)
        else:
            blocks.append(cur)
    return blocks


# ---------------------------------------------------------------------------
# Structured template fallback (never "unknown", never "0 minutes")
# ---------------------------------------------------------------------------

def _template_description(sig: DaySignals, elicited: list) -> str:
    """[R08 SS5] AI fills Gibbs phase 1 with structured facts. Always non-empty."""
    parts: list[str] = []

    dur = sig.duration_minutes
    if dur > 0:
        state_suffix = f"（{sig.state_label}模式）" if sig.state_label else ""
        parts.append(f"在「{sig.bucket_label}」活動上持續 {dur:.0f} 分鐘{state_suffix}")
    elif sig.app_bucket and sig.app_bucket != "unknown":
        parts.append(f"進行「{sig.bucket_label}」類型活動")

    if sig.wpm_avg > 0:
        parts.append(f"平均輸入速率 {sig.wpm_avg:.0f} WPM")

    for trans in sig.state_transitions[:2]:
        label = _STATE_LABEL.get(trans, trans)
        parts.append(f"狀態轉換至「{label}」")

    for bp, conf in zip(sig.breakpoint_types[:2], sig.breakpoint_confidences[:2]):
        label = _BREAKPOINT_LABEL.get(bp, bp)
        parts.append(f"系統偵測到{label}（信心值 {conf:.0%}）")

    for e in elicited:
        project = e.get("project") if isinstance(e, dict) else getattr(e, "project", "")
        minutes = e.get("duration_minutes") if isinstance(e, dict) else getattr(e, "minutes", 0)
        if project:
            parts.append(f"自述「{project}」花費約 {minutes} 分鐘")

    if not parts:
        return "今日無足夠活動資料可供描述。"
    return "；".join(parts) + "。"


def _template_analysis(signals: list[DaySignals], elicited: list) -> str:
    """[R08 SS5] Gibbs phase 2: initial analysis. No subjective content."""
    total_mins = sum(s.duration_minutes for s in signals)
    for e in elicited:
        if isinstance(e, dict):
            total_mins += e.get("duration_minutes", 0)
        else:
            total_mins += getattr(e, "minutes", 0)

    buckets = [s.bucket_label for s in signals if s.app_bucket and s.app_bucket != "unknown"]
    states = [s.state_label for s in signals if s.state_label]
    bucket_str = "、".join(dict.fromkeys(buckets)) if buckets else "未分類活動"
    state_str = "、".join(dict.fromkeys(states)) if states else ""

    summary = f"全日主要活躍 {total_mins:.0f} 分鐘，涵蓋 {bucket_str}"
    if state_str:
        summary += f"，主要狀態：{state_str}"
    summary += "。（主觀感受與行動計畫請您親自填寫）"
    return summary


# ---------------------------------------------------------------------------
# Privacy-safe prompt builders
# ---------------------------------------------------------------------------

def _build_local_prompt(sig: DaySignals, elicited: list, ctx: Any = None) -> str:
    """
    Full signal set for local Gemma. Produces a HIGH-LEVEL title + one-line description,
    using content_summary as the primary material (telemetry numbers are secondary).

    [RISK-15] L1 allowed here: content_summary, goals.title, promises.text,
              role_projects.name, chat_digest summaries from M2.2.2.
              Output is stored locally; M6.2 generalises before any cloud sync.
    """
    program = friendly_app_name(sig.app_name) or sig.bucket_label
    lines = [
        "你是 coOS 日報助理。請根據以下一段活動的「內容摘要」，產出一張高階日報卡片。",
        "要求：",
        "1. title：一個 6-16 字、具體且高層次的活動主題（例如「coOS 社群前端設計調校」、",
        "   「網路喜劇影片觀賞」、「研究 Transformer 架構」）。不要用程式名或「其他應用」當標題。",
        "2. description：一句話（30-60 字）描述使用者具體做了什麼，綜合多筆內容摘要的主題。",
        "3. 只描述客觀事實，不要加主觀評語、不要寫感受或建議（那是使用者要填的）。",
        "4. 嚴格輸出 JSON：{\"title\": \"...\", \"description\": \"...\"}，不要其他文字。",
        "",
        f"使用程式：{program}",
        f"持續時間：{sig.duration_minutes:.0f} 分鐘",
    ]
    if sig.content_summaries:
        # [RISK-15] content_summary is L1 -- only sent to local LLM here. This is the SPINE.
        # Cap to ~900 chars total to avoid Ollama near-timeout edge case with long prompts.
        uniq = list(dict.fromkeys(sig.content_summaries))
        selected: list[str] = []
        budget = 900
        for s in uniq[:8]:
            entry = s[:150]  # hard cap per summary
            if budget - len(entry) - 2 < 0:
                break
            selected.append(entry)
            budget -= len(entry) + 2
        joined = "\n".join(f"- {s}" for s in selected)
        lines.append("內容摘要（主要依據，請綜合歸納主題）：")
        lines.append(joined)
    if sig.state_label:
        lines.append(f"活動狀態：{sig.state_label}")
    if sig.wpm_avg > 0:
        lines.append(f"平均輸入速率：{sig.wpm_avg:.0f} WPM")
    for e in elicited:
        project = e.get("project") if isinstance(e, dict) else getattr(e, "project", "")
        minutes = e.get("duration_minutes") if isinstance(e, dict) else getattr(e, "minutes", 0)
        if project:
            lines.append(f"自述任務：{project}（{minutes} 分鐘）")
    if ctx is not None:
        if ctx.active_projects:
            names = "、".join(p["name"] for p in ctx.active_projects[:3] if p.get("name"))
            if names:
                lines.append(f"作用中專案：{names}")
        for g in ctx.active_goals[:2]:
            title = g.get("title", "")
            progress = g.get("progress", 0.0)
            if title:
                lines.append(f"目標：{title}（進度 {progress:.0%}）")
        for p in ctx.due_promises[:2]:
            text = p.get("text", "")
            deadline = p.get("deadline", "")
            if text:
                suffix = f"（截止 {deadline}）" if deadline else ""
                lines.append(f"待辦承諾：{text}{suffix}")
        for intent in [i for i in ctx.intent_summaries if i.get("source") == "chat_digest"][:2]:
            summary = intent.get("summary", "")
            if summary:
                lines.append(f"對話意圖摘要：{summary}")
    return "\n".join(lines)


def _build_cloud_prompt(sig: DaySignals, elicited: list, ctx: Any = None) -> str:
    """
    Privacy-safe subset for Gemini Flash.
    [RISK-15] EXCLUDED: content_summary, goals.title, promises.text,
              role_projects.name, chat_digest summaries.
    INCLUDED: app_bucket labels, durations, wpm, activity_state, breakpoints,
              goals.progress (numeric), pending promises count, telemetry intent_labels (L2).
    """
    lines = [
        "You are a daily reflection assistant for coOS. Write a 80-150 character",
        "Gibbs Reflection Phase 1 (objective description) in Traditional Chinese.",
        "Describe only objective facts. No subjective commentary.",
        "",
        f"App category: {sig.bucket_label}",
        f"Duration: {sig.duration_minutes:.0f} minutes",
    ]
    if sig.wpm_avg > 0:
        lines.append(f"Typing rate: {sig.wpm_avg:.0f} WPM")
    if sig.state_label:
        lines.append(f"Activity state: {sig.state_label}")
    if sig.state_transitions:
        labels = [_STATE_LABEL.get(t, t) for t in sig.state_transitions[:3]]
        lines.append(f"State transitions: {'->'.join(labels)}")
    if sig.breakpoint_types:
        bps = [_BREAKPOINT_LABEL.get(b, b) for b in sig.breakpoint_types[:3]]
        lines.append(f"Breakpoint signals: {', '.join(bps)}")
    # content_summary, project names, goal titles, promise text EXCLUDED -- RISK-15
    for e in elicited:
        project = e.get("project") if isinstance(e, dict) else getattr(e, "project", "")
        minutes = e.get("duration_minutes") if isinstance(e, dict) else getattr(e, "minutes", 0)
        if project:
            lines.append(f"Self-reported task: {project} ({minutes} min)")
    if ctx is not None:
        if ctx.active_goals:
            vals = [g.get("progress", 0.0) for g in ctx.active_goals if g.get("progress") is not None]
            if vals:
                lines.append(f"Active goals: {len(vals)}, avg progress {sum(vals)/len(vals):.0%}")
        if ctx.due_promises:
            lines.append(f"Pending promises due today: {len(ctx.due_promises)}")
        telemetry_intents = [i for i in ctx.intent_summaries if i.get("source") == "telemetry"]
        tl = list(dict.fromkeys(i.get("label", "") for i in telemetry_intents[:3] if i.get("label")))
        if tl:
            lines.append(f"Telemetry intent labels: {', '.join(tl)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM callers
# ---------------------------------------------------------------------------

async def _call_local_gemma_once(
    prompt: str, base_url: str, model: str, timeout: float = 90.0
) -> tuple[str, str, str | None, int | None, int | None, int]:
    """Single attempt. Returns (text, status, error_msg, completion_tokens, prompt_tokens, latency_ms)."""
    import httpx
    import time as _t
    url = f"{base_url}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.3,
        "stream": False,
    }
    t0 = _t.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        latency_ms = int((_t.monotonic() - t0) * 1000)
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
        usage = data.get("usage") or {}
        ct = usage.get("completion_tokens")
        pt = usage.get("prompt_tokens")
        if not text:
            return "", "empty_response", None, ct, pt, latency_ms
        return text, "success", None, ct, pt, latency_ms
    except Exception as e:
        latency_ms = int((_t.monotonic() - t0) * 1000)
        return "", "failed", str(e), None, None, latency_ms


async def _call_local_gemma(prompt: str, ai_local_host: str, model: str = "gemma-4-e4b-it-4bit") -> str | None:
    """Call local Gemma via the shared InferencePriorityQueue (priority=3).

    Routing through enqueue_inference ensures M4.4/gibbs and M2.2 telemetry never
    hit Ollama simultaneously (which causes KV cache pressure → empty responses).

    Retry policy:
      - fast-reject (latency < 2 s, empty): cool down 3 s, retry once.
      - near-timeout (latency > 15 s, empty): skip retry — another 90 s wasted.
      - failed (network error): no retry.
    """
    import asyncio as _asyncio

    base = ai_local_host if ai_local_host.startswith("http") else f"http://{ai_local_host}"
    base = base.rstrip("/")

    def _emit_log(status: str, text: str, error_msg: str | None, ct, pt, latency_ms: int) -> None:
        try:
            from m0_4_logging.writer import get_logger as _get_log_writer
            _asyncio.ensure_future(
                _get_log_writer().emit_llm_log(
                    model_name=model,
                    caller_module="M4.4/gibbs",
                    prompt_text=prompt[:2000],
                    response_text=text,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    latency_ms=latency_ms,
                    temperature=0.3,
                    status=status,
                    error_message=error_msg,
                )
            )
        except Exception:
            pass

    from m2_2_gemma.queue import enqueue_inference

    for attempt in range(2):
        if attempt > 0:
            await _asyncio.sleep(3.0)

        # Capture by default arg to avoid closure-over-mutable-loop-var issues
        async def _one_attempt(_p=prompt, _b=base, _m=model):
            return await _call_local_gemma_once(_p, _b, _m)

        try:
            text, status, err, ct, pt, latency_ms = await enqueue_inference(
                priority=3, fn=_one_attempt, tag="gibbs"
            )
        except Exception as exc:
            logger.warning("[M4.4] enqueue_inference raised: %s", exc)
            return None

        _emit_log(status, text, err, ct, pt, latency_ms)

        if status == "success":
            return text

        if status == "empty_response":
            if latency_ms > 15_000:
                # Near-timeout: Ollama generated nothing in 15+ seconds.
                # Retrying would waste another ~90 s. Fall through to fallback.
                logger.info("[M4.4] Near-timeout empty (%dms), skip retry", latency_ms)
                break
            if attempt == 0:
                # Fast-reject (<2 s): Ollama VRAM/KV cache pressure. Cool down then retry.
                logger.info("[M4.4] Fast-reject empty (%dms), retry in 3s...", latency_ms)
                continue

        logger.info("[M4.4] Gemma %s attempt %d (%dms): %s", status, attempt + 1, latency_ms, err or "empty")
        break

    return None


async def _call_gemini_flash(prompt: str, api_key: str, model: str = "gemini-2.0-flash") -> str | None:
    """
    Call Gemini Flash via Google Generative AI SDK.
    [RISK-15] Cloud path -- caller must ensure content_summary is NOT in prompt.
    """
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(model)
        response = await asyncio.to_thread(
            gemini_model.generate_content,
            prompt,
        )
        text = response.text.strip() if response.text else ""
        return text if text else None
    except Exception as e:
        logger.warning("[M4.4] Gemini Flash fallback failed: %s", e)
        return None


@dataclass
class GibbsCard:
    """Structured high-level card output for one activity block."""
    title: str
    description: str
    inference_mode: str = "template"  # gemma_edge | gemini_cloud | template


def _parse_card_json(raw: str) -> tuple[str, str] | None:
    """Parse {"title": ..., "description": ...} from an LLM response. None on failure."""
    import json
    import re
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    title = str(data.get("title", "")).strip()
    desc = str(data.get("description", "")).strip()
    if not title and not desc:
        return None
    return title, desc


def _template_card(sig: DaySignals, elicited: list) -> GibbsCard:
    """
    Structured fallback when no LLM is available.
    Title = friendly program name + duration. Description = each content_summary on its own line
    (no mid-sentence truncation), plus telemetry evidence at the end.
    """
    program = friendly_app_name(sig.app_name) or sig.bucket_label
    dur = sig.duration_minutes

    if sig.content_summaries:
        # Deduplicate while preserving order; show up to 4 full sentences.
        uniq = list(dict.fromkeys(sig.content_summaries))[:4]
        desc_lines = [f"• {s}" for s in uniq]
        # Append brief telemetry evidence (state + WPM)
        evidence: list[str] = []
        if sig.state_label:
            evidence.append(sig.state_label)
        if sig.wpm_avg > 5:
            evidence.append(f"{sig.wpm_avg:.0f} WPM")
        if dur > 0:
            evidence.append(f"約 {dur:.0f} 分鐘")
        if evidence:
            desc_lines.append(f"[{' · '.join(evidence)}]")
        desc = "\n".join(desc_lines)
        # Title = program name + duration bracket; omit the raw English anchor
        title = f"{program}（{dur:.0f} 分鐘）" if dur > 0 else program
    else:
        title = f"{program}（{dur:.0f} 分鐘）" if dur > 0 else program
        desc = _template_description(sig, elicited)
    return GibbsCard(title=title or program or "活動區塊", description=desc, inference_mode="template")


async def _generate_card(
    sig: DaySignals,
    elicited: list,
    ai_local_host: str,
    gemini_api_key: str,
    ctx: Any = None,
    gemma_model: str = "gemma-4-e4b-it-4bit",
) -> GibbsCard:
    """
    Generate a high-level {title, description} card for one activity block.
    [RISK-15] content_summary only goes to local Gemma. Cloud path gets no L1 text and
    therefore cannot produce a content-specific title -- it yields a structured description
    only, and the title falls back to the program/bucket label.
    Order: local Gemma (rich) -> Gemini cloud (generic) -> template (structured).
    """
    # Local Gemma: full content_summary context -> can produce a specific title
    if ai_local_host:
        raw = await _call_local_gemma(_build_local_prompt(sig, elicited, ctx), ai_local_host, model=gemma_model)
        parsed = _parse_card_json(raw) if raw else None
        if parsed:
            title, desc = parsed
            program = friendly_app_name(sig.app_name) or sig.bucket_label
            return GibbsCard(
                title=title or program or "活動區塊",
                description=desc or _template_card(sig, elicited).description,
                inference_mode="gemma_edge",
            )

    # Gemini cloud: privacy-safe, no L1 -> generic description, program-derived title
    if gemini_api_key:
        raw = await _call_gemini_flash(_build_cloud_prompt(sig, elicited, ctx), gemini_api_key)
        if raw:
            program = friendly_app_name(sig.app_name) or sig.bucket_label
            dur = sig.duration_minutes
            title = f"{program}（{dur:.0f} 分鐘）" if dur > 0 else program
            return GibbsCard(title=title or "活動區塊", description=raw.strip(), inference_mode="gemini_cloud")

    logger.warning(
        "[M4.4] Both LLMs unavailable for app=%s bucket=%s duration_s=%d; template card fallback",
        sig.app_name, sig.app_bucket, sig.duration_s,
    )
    return _template_card(sig, elicited)


async def _generate_one(
    sig: DaySignals,
    elicited: list,
    ai_local_host: str,
    gemini_api_key: str,
    ctx: Any = None,
    gemma_model: str = "gemma-4-e4b-it-4bit",
) -> str:
    """Back-compat shim: returns just the description string of the generated card."""
    card = await _generate_card(sig, elicited, ai_local_host, gemini_api_key, ctx, gemma_model=gemma_model)
    return card.description


# ---------------------------------------------------------------------------
# Public API (called by draft_scheduler.py)
# ---------------------------------------------------------------------------

async def build_gibbs_cards(
    logs: list,
    elicited: list,
    ai_local_host: str = "http://192.168.0.79:11434",
    gemini_api_key: str = "",
    ctx: Any = None,
    gemma_model: str = "gemma-4-e4b-it-4bit",
) -> tuple[list[DaySignals], list[GibbsCard]]:
    """
    Build high-level {title, description} cards for merged activity blocks.

    Pipeline: group_signals (per focus session) -> merge_into_blocks (collapse
    fragmentation) -> _generate_card (content_summary-driven LLM, title + description).

    Returns (blocks, cards) so the caller has both the merged signal metadata
    (app_bucket, activity_state, end_timestamp_iso, duration) and the rendered cards.
    """
    signals = group_signals(logs)
    if not signals:
        return [], []
    blocks = merge_into_blocks(signals)

    # Serialise Gemma calls: the iPad M1 inference engine is single-threaded.
    # Parallel requests queue up and all time out; sequential ensures each card
    # actually gets a response. Cloud Gemini calls can run in parallel later if needed.
    cards: list[GibbsCard] = []
    for sig in blocks:
        card = await _generate_card(sig, elicited, ai_local_host, gemini_api_key, ctx, gemma_model=gemma_model)
        cards.append(card)
    return blocks, cards


async def build_gibbs_description(
    logs: list,
    elicited: list,
    ai_local_host: str = "http://192.168.0.79:11434",
    gemini_api_key: str = "",
    ctx: Any = None,
    gemma_model: str = "gemma-4-e4b-it-4bit",
) -> tuple[list[DaySignals], list[str]]:
    """
    Back-compat wrapper around build_gibbs_cards: returns (blocks, descriptions).
    Applies semantic merging so callers no longer get fragmented per-session output.
    """
    blocks, cards = await build_gibbs_cards(logs, elicited, ai_local_host, gemini_api_key, ctx, gemma_model=gemma_model)
    if not blocks:
        return [], ["今日無可供描述的活動紀錄。"]
    return blocks, [c.description for c in cards]


def build_gibbs_analysis(
    signals: list[DaySignals],
    elicited: list,
) -> str:
    """
    Gibbs phase 2: initial analysis (AI fills, synchronous).
    [R08 SS5] Explicitly withholds subjective commentary; instructs user to fill phases 3-5.
    """
    return _template_analysis(signals, elicited)


def derive_segment_title(sig: DaySignals) -> str:
    """
    Derive a human-readable segment title from app_bucket + activity_state.
    Used by m6_4_daily_timeline and create_draft_reflection to replace non-existent 'project' column.
    """
    bucket = sig.bucket_label
    state = sig.state_label
    dur = sig.duration_minutes

    if state:
        return f"{bucket} · {state}"
    if dur > 0:
        return f"{bucket}（{dur:.0f} 分鐘）"
    return bucket
