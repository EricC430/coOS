"""
M4.2.2 -- Nightly Reflection Job

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R11: Park et al. ss3.3] Reflection: observations -> higher-order insights
Cron slot: 02:30 (after 02:00 drafts, before 03:00 rule miner)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReflectionResult:
    """Result of a nightly reflection job for one persona."""
    persona_id: str
    role_id: str
    reflections_created: int
    observation_count: int


def summarize_observations(observations: list[dict]) -> list[str]:
    """
    [R11 ss3.3] Summarize daily observations into 1-3 reflection strings.

    MVP: rule-based grouping. Future: Gemma edge model for deeper synthesis.
    Each observation dict has: {"content": str, "importance": float, "kind": str}
    """
    if not observations:
        return []

    # Sort by importance descending
    sorted_obs = sorted(observations, key=lambda o: o.get("importance", 0.5), reverse=True)

    # Group top observations into reflections
    reflections: list[str] = []

    # Most important observation becomes a reflection
    if sorted_obs:
        top = sorted_obs[0]
        reflections.append(
            f"Key insight: {top.get('content', '')} "
            f"(importance: {top.get('importance', 0.5):.1f})"
        )

    # If there are commitments, summarize them
    commitments = [o for o in sorted_obs if o.get("kind") == "commitment"]
    if commitments:
        commit_texts = [c.get("content", "") for c in commitments[:3]]
        reflections.append("Active commitments: " + "; ".join(commit_texts))

    # Patterns across observations
    if len(sorted_obs) >= 3:
        topics = [o.get("content", "")[:30] for o in sorted_obs[:3]]
        reflections.append("Recurring themes today: " + ", ".join(topics))

    return reflections[:3]  # Cap at 3
"""
"""
