"""M2.2 RuleBasedExtractor -- degraded inference when ai.local is unreachable

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.4
Activated when: GemmaEdgeClient raises ConnectError or TimeoutException.
RISK-05: source_log_id and role_id MUST remain non-empty in fallback mode.
inference_mode must be set to 'rule_based_fallback' so M5.1 can adjust confidence.
"""

from __future__ import annotations

import re

_INTENT_KEYWORDS: dict[str, str] = {
    r"debug|error|exception|traceback|fix": "debugging_session",
    r"calculus|integral|derivative|math|homework": "math_study",
    r"test|pytest|unittest|assert": "testing_activity",
    r"sql|database|db|query|migration": "database_development",
    r"read|doc|reference|mdn|stack": "documentation_reading",
    r"commit|push|pull|merge|git": "version_control_activity",
    r"write|essay|report|draft": "writing_task",
}

_FRUSTRATION_SIGNALS = {
    r"error|exception|fail|crash|bug|wrong|broken": 0.6,
    r"retry|again|still|doesn.t work": 0.4,
}


class RuleBasedExtractor:
    """Lightweight keyword + regex extractor used when Gemma is unavailable.

    Produces a valid IntentVector-compatible dict with inference_mode='rule_based_fallback'.
    Semantic quality is lower than Gemma, but RISK-05 invariants are preserved.
    """

    def extract(self, text: str) -> dict:
        lower = text.lower()

        intent_label = "unknown_ambient_activity"
        for pattern, label in _INTENT_KEYWORDS.items():
            if re.search(pattern, lower):
                intent_label = label
                break

        frustration = 0.0
        for pattern, score in _FRUSTRATION_SIGNALS.items():
            if re.search(pattern, lower):
                frustration = max(frustration, score)

        # Crude stripped_entities_count: count distinct capitalized tokens
        entities = set(re.findall(r"\b[A-Z][a-zA-Z_0-9]{2,}\b", text))
        stripped = len(entities)

        return {
            "intent_label": intent_label,
            "context_summary": f"rule_based: {intent_label}",
            "frustration_level": frustration,
            "valence": 0.0,
            "arousal": 0.0,
            "stripped_entities_count": stripped,
            "semantic_embedding": [],
        }
