"""
M4.4.3 -- Nightly Draft Scheduler

SPEC: docs/modules/M4_4_natural_elicitation_draft_SPEC.md SS7.3
[R10 SSMindScape + R08 SS6.2 Gibbs Cycle]

[RISK-01] Produced drafts always have is_draft=True, is_reviewed=False -- never auto-approved.
[RISK-15] ai_description is generated from generalised metrics only when going to cloud LLM;
          content_summary stays inside local Gemma. Eguard second-layer sanitisation applied
          before any text is written to daily_reflection_segments.
[RISK-06] Draft strictly scoped to current role_id.

Schedule: default 02:00 daily (staggered from M4.1.5 at 03:00, see M4.1 SPEC SS9).
          Customisable via role_settings.daily_report_time.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from .gibbs_template import (
    DaySignals,
    GibbsCard,
    build_gibbs_cards,
    build_gibbs_analysis,
    friendly_app_name,
)
from .role_inference import RoleCandidate, build_candidates, infer_role

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Eguard generalisation (second-layer PII defence, RISK-15)
# ---------------------------------------------------------------------------

def _eguard_generalize(text: str, role_id: str = "") -> str:
    """
    [RISK-15] Second sanitisation pass: mask any residual PII even after
    gibbs_template has structurally excluded content_summary.
    Degrades gracefully to passthrough when Eguard is unavailable.
    """
    try:
        from m2_3_eguard.filter import EguardFilter
        return EguardFilter().mask_pii(text, role_id=role_id).sanitized_text
    except Exception as e:
        logger.warning("[M4.4] Eguard generalise unavailable, passthrough: %s", e)
        return text


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------

def _get_gemini_key() -> str:
    """Read GEMINI_API_KEY from environment / settings without crashing."""
    try:
        from config import settings
        return getattr(settings, "gemini_api_key", "") or ""
    except Exception:
        pass
    import os
    return os.environ.get("GEMINI_API_KEY", "")


def _get_ai_local_host() -> str:
    try:
        from config import settings
        return getattr(settings, "ai_local_host", "http://192.168.0.79:11434") or "http://192.168.0.79:11434"
    except Exception:
        return "http://192.168.0.79:11434"


def _get_gemma_model() -> str:
    try:
        from config import settings
        return getattr(settings, "gemma_model", "gemma-4-e4b-it-4bit") or "gemma-4-e4b-it-4bit"
    except Exception:
        return "gemma-4-e4b-it-4bit"


# ---------------------------------------------------------------------------
# Single-role draft generation
# ---------------------------------------------------------------------------

async def generate_draft(
    user_id: str,
    role_id: str,
    reflection_date: date,
    db: Any,
    is_primary_role: bool = True,
) -> Any | None:
    """
    Assemble a Gibbs reflection draft for one role for a given day.

    Activity blocks are attributed per-role (RISK-06). A block that confidently belongs
    to a different role is skipped. Blocks with NO confident attribution go to the
    PRIMARY role only (is_primary_role=True) -- avoids duplicating unassigned activity
    across every role's draft.

    Returns None if there are no attributable blocks (no empty reflections -- SPEC SS7.5).

    [RISK-01] is_draft=True / is_reviewed=False / subjective fields None.
    [RISK-15] content_summary routed to local LLM only; cloud LLM receives anonymised subset.
    """
    logs = await db.fetch_tracking_logs(user_id, role_id, reflection_date)
    if not logs:
        return None

    elicited = await db.fetch_elicited_durations(user_id, role_id, reflection_date)

    # [M4.4.3] Fetch snapshot context: role_projects, goals, promises, intent_logs (incl. chat_digest)
    ctx = None
    if hasattr(db, "fetch_daily_context"):
        try:
            ctx = await db.fetch_daily_context(user_id, role_id, reflection_date)
        except Exception as _ctx_err:
            logger.warning("[M4.4] fetch_daily_context failed (non-fatal): %s", _ctx_err)

    # [RISK-06] Cross-role anchor map for attribution. Built from every role's OWN
    # projects/goals; inference compares a block only against each candidate's anchors.
    candidates: list[RoleCandidate] = []
    if hasattr(db, "fetch_role_anchor_map"):
        try:
            anchor_map = await db.fetch_role_anchor_map(user_id)
            candidates = build_candidates(anchor_map)
        except Exception as _ae:
            logger.warning("[M4.4] fetch_role_anchor_map failed (non-fatal): %s", _ae)

    ai_local_host = _get_ai_local_host()
    gemini_api_key = _get_gemini_key()
    gemma_model = _get_gemma_model()

    # Merged activity blocks + high-level {title, description} cards.
    # ctx enriches the LLM prompt; privacy routing handled inside gibbs_template.
    blocks, cards = await build_gibbs_cards(
        logs, elicited,
        ai_local_host=ai_local_host,
        gemini_api_key=gemini_api_key,
        ctx=ctx,
        gemma_model=gemma_model,
    )

    if not blocks:
        return None

    ai_analysis = build_gibbs_analysis(blocks, elicited)

    source_log_ids = [
        log["id"] if isinstance(log, dict) else getattr(log, "id", None)
        for log in logs
    ]

    first_draft = None
    emitted = 0
    for i, (sig, card) in enumerate(zip(blocks, cards)):
        # [RISK-06] Attribute this block. Text = de-identified content summaries + app name.
        # If it confidently belongs to a DIFFERENT role, skip it here (it surfaces in that
        # role's own draft). Below threshold -> keep with current role (neutral default).
        block_text = " ".join(sig.content_summaries) + " " + friendly_app_name(sig.app_name)
        if candidates:
            inferred_role, score, confident = infer_role(block_text, candidates, fallback_role_id=role_id)
            if confident and inferred_role != role_id:
                logger.debug(
                    "[M4.4/RISK-06] block attributed to role=%s (score=%.2f), skipping for role=%s",
                    inferred_role, score, role_id,
                )
                continue
            # Unattributed block (not confident) -> only the primary role keeps it,
            # so it does not duplicate across every role's draft.
            if not confident and not is_primary_role:
                continue

        # [RISK-15] L1 high-level card stored locally; generalized variant for cloud sync.
        # ai_description holds the rich local text; ai_description_generalized is masked.
        generalized_desc = _eguard_generalize(card.description, role_id=role_id)
        generalized_title = _eguard_generalize(card.title, role_id=role_id)

        draft = await db.create_draft_reflection(
            user_id=user_id,
            role_id=role_id,
            reflection_date=reflection_date,
            title=card.title,                              # L1 high-level title (local only)
            title_generalized=generalized_title,           # cloud-safe title
            ai_description=card.description,                # L1 rich description (local only)
            ai_description_generalized=generalized_desc,   # cloud-safe description (RISK-15)
            ai_analysis=ai_analysis if emitted == 0 else "",
            source_log_ids=source_log_ids if emitted == 0 else [],
            activity_minutes=sig.duration_minutes,
            app_bucket=sig.app_bucket,
            app_name=sig.app_name,
            activity_state=sig.activity_state,
            end_timestamp_iso=sig.end_timestamp_iso,
            inference_mode=card.inference_mode,
            # [RISK-01] Subjective fields always None -- never auto-filled.
            is_draft=True,
            is_reviewed=False,
            user_feeling=None,
            user_action_plan=None,
        )
        if first_draft is None:
            first_draft = draft
        emitted += 1

    return first_draft


# ---------------------------------------------------------------------------
# Scheduler entry point
# ---------------------------------------------------------------------------

async def _compress_undigested_threads(
    role_id: str,
    for_date: date,
    db: Any,
    ai_local_host: str,
) -> None:
    """
    [M2.2.2] Compress any threads from for_date that were never split (i.e. the user's
    last session of the day ended without triggering an inactivity split).
    Called by run_draft_cron before draft generation so chat_digest intent_logs are
    available to enrich the Gibbs prompt.

    Finds threads that have chat_transcripts on for_date but no chat_digest in intent_logs,
    then calls ChatCompressor.compress_thread() for each.
    """
    try:
        from m2_2_gemma.chat_compressor import ChatCompressor
        from config import settings as _cfg
        model = getattr(_cfg, "gemma_model", "gemma-4-e4b-it-4bit")
    except Exception as e:
        logger.warning("[M4.4/M2.2.2] ChatCompressor import failed (non-fatal): %s", e)
        return

    # Find distinct thread_ids for this role on for_date that have no chat_digest yet
    try:
        date_str = for_date.isoformat()
        undigested = await db.fetch_all(
            "SELECT DISTINCT thread_id FROM chat_transcripts "
            "WHERE role_id = :rid AND date(created_at) = :dt "
            "AND thread_id NOT IN ("
            "  SELECT source_log_id FROM intent_logs "
            "  WHERE role_id = :rid AND source_type = 'chat_digest'"
            ")",
            {"rid": role_id, "dt": date_str},
        )
    except Exception as e:
        logger.warning("[M4.4/M2.2.2] fetch undigested threads failed for role=%s: %s", role_id, e)
        return

    if not undigested:
        return

    compressor = ChatCompressor(ai_local_host=ai_local_host, model=model)
    for row in undigested:
        tid = row["thread_id"] if hasattr(row, "__getitem__") else getattr(row, "thread_id", None)
        if not tid:
            continue
        try:
            written = await compressor.compress_thread(thread_id=tid, role_id=role_id, db=db)
            if written:
                logger.info("[M4.4/M2.2.2] cron compressed undigested thread=%s role=%s", tid, role_id)
        except Exception as e:
            logger.warning("[M4.4/M2.2.2] compress failed for thread=%s: %s", tid, e)


async def run_draft_cron(
    user_id: str,
    db: Any,
    today: date | None = None,
) -> list:
    """
    Daily scheduler entry (default 02:00, triggered by arq).

    Generates drafts for yesterday for every active role.
    Before generating, compresses any chat threads from yesterday that were never
    split by inactivity (M2.2.2 catch-all so chat_digest context is available).
    `today` can be injected for tests (avoids freezegun / wall clock dependency).
    """
    if today is None:
        today = date.today()
    yesterday = today - timedelta(days=1)
    ai_local_host = _get_ai_local_host()

    roles = await db.get_user_active_roles(user_id)
    drafts: list = []
    for idx, role in enumerate(roles):
        role_id = role["id"] if isinstance(role, dict) else getattr(role, "id")

        # [M2.2.2] Compress threads that ended without an inactivity split
        await _compress_undigested_threads(role_id, yesterday, db, ai_local_host)

        try:
            # First active role is the primary -- it keeps unattributed blocks (RISK-06).
            draft = await generate_draft(
                user_id, role_id, yesterday, db=db, is_primary_role=(idx == 0)
            )
        except Exception as e:
            # SPEC SS7.5: single-role failure must not abort other roles
            logger.warning(
                "[M4.4] draft generation failed for role=%s: %s", role_id, e, exc_info=True
            )
            continue
        if draft is not None:
            drafts.append(draft)

    return drafts
