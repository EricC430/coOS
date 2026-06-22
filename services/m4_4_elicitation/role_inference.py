"""
M4.4.4 -- Role Attribution Inference

Telemetry rows almost always carry role_id = NULL / 'default' (the M1.1 daemon does
not tag the active role). Without attribution, every focus block lands in whichever
role happened to be queried first. This module infers the most likely role for an
activity block by matching its de-identified content against each role's own
projects / goals.

[RISK-06] Cross-role leakage guard:
  - Inference compares a block ONLY against the candidate role's own projects/goals;
    no implicit state crosses roles.
  - A confidence threshold gates attribution. Below threshold the block stays with the
    fallback (currently-active) role rather than being mis-assigned -- "rather neutral
    than wrong" (RISK-06 mitigation principle).

[RISK-15] content_summary is L1 plaintext. This module reads it locally only to compute
  a match score; it never emits content_summary outward. The returned value is just a
  role_id + score.

Matching is keyword/token overlap based (deterministic, offline). A future revision may
escalate to local Gemma semantic similarity, but the threshold-gated contract stays.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Minimum normalized overlap score required to attribute a block to a non-fallback role.
# Below this, the block stays with the active/fallback role (RISK-06: never mis-assign).
ROLE_MATCH_THRESHOLD = 0.18

# App-name hints that bias toward "work/study" vs "leisure" without naming a role.
# Used only as a weak tie-breaker, never as the sole signal.
_TOKEN_SPLIT = re.compile(r"[\s/\\,\.;:_\-\(\)\[\]{}　，、。]+")


@dataclass
class RoleCandidate:
    """One role plus its attribution anchors (project names + goal titles)."""
    role_id: str
    anchors: list[str] = field(default_factory=list)  # L1 strings: project/goal names

    def tokenize(self) -> set[str]:
        toks: set[str] = set()
        for a in self.anchors:
            toks |= _tokenize(a)
        return toks


def _tokenize(text: str) -> set[str]:
    """Lowercase token set; for CJK also include 2-gram shingles so '社群頁面' matches."""
    if not text:
        return set()
    low = text.lower()
    words = {t for t in _TOKEN_SPLIT.split(low) if len(t) >= 2}
    # CJK bigrams: improves matching for languages without whitespace word boundaries
    cjk = re.findall(r"[一-鿿]{2,}", low)
    for run in cjk:
        for i in range(len(run) - 1):
            words.add(run[i:i + 2])
    return words


def build_candidates(role_anchor_map: dict[str, list[str]]) -> list[RoleCandidate]:
    """
    role_anchor_map: {role_id: [project_name, goal_title, ...]}.
    Built by the caller from each role's own projects/goals (RISK-06: per-role only).
    """
    return [RoleCandidate(role_id=rid, anchors=anchors) for rid, anchors in role_anchor_map.items()]


def score_block(block_text: str, candidate: RoleCandidate) -> float:
    """
    Normalized token-overlap score in [0, 1] between a block's de-identified text
    (content summaries + app names) and one role's anchors.
    """
    block_toks = _tokenize(block_text)
    if not block_toks:
        return 0.0
    cand_toks = candidate.tokenize()
    if not cand_toks:
        return 0.0
    overlap = block_toks & cand_toks
    if not overlap:
        return 0.0
    # Jaccard-ish but biased toward block coverage (how much of the block the role explains)
    return len(overlap) / len(block_toks)


def infer_role(
    block_text: str,
    candidates: list[RoleCandidate],
    fallback_role_id: str,
    threshold: float = ROLE_MATCH_THRESHOLD,
) -> tuple[str, float, bool]:
    """
    Return (role_id, score, confident).

    [RISK-06] If the best score is below `threshold`, returns the fallback role with
    confident=False -- the caller should treat this as "unattributed, kept with active
    role" rather than a positive cross-role assignment.
    """
    if not candidates:
        return fallback_role_id, 0.0, False

    best_id = fallback_role_id
    best_score = 0.0
    for cand in candidates:
        s = score_block(block_text, cand)
        if s > best_score:
            best_score = s
            best_id = cand.role_id

    if best_score >= threshold:
        return best_id, best_score, True
    # Below threshold: stay neutral with the fallback (active) role
    return fallback_role_id, best_score, False
