"""M2.2 RuleBasedExtractor -- degraded inference when ai.local is unreachable

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.4
Activated when: GemmaEdgeClient raises ConnectError or TimeoutException.
RISK-05: source_log_id and role_id MUST remain non-empty in fallback mode.
inference_mode must be set to 'rule_based_fallback' so M5.1 can adjust confidence.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_INTENT_KEYWORDS: dict[str, str] = {
    r"debug|error|exception|traceback|fix": "debugging_session",
    r"calculus|integral|derivative|math|homework": "math_study",
    r"test|pytest|unittest|assert": "testing_activity",
    r"sql|database|db|query|migration": "database_development",
    r"read|doc|reference|mdn|stack": "documentation_reading",
    r"commit|push|pull|merge|git": "version_control_activity",
    r"write|essay|report|draft": "writing_task",
}

DEFAULT_FRUSTRATION_SIGNALS: dict[str, float] = {
    r"error|exception|fail|crash|bug|wrong|broken": 0.6,
    r"retry|again|still|doesn.t work": 0.4,
}


class RuleBasedExtractor:
    """Lightweight keyword + regex extractor used when Gemma is unavailable.

    Produces a valid IntentVector-compatible dict with inference_mode='rule_based_fallback'.
    Semantic quality is lower than Gemma, but RISK-05 invariants are preserved.
    """

    def __init__(self, rules_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        if rules_path:
            self._rules_path = rules_path
        else:
            settings = get_settings()
            self._rules_path = settings.local_db_path.parent / "fallback_rules.json"

        self._intent_keywords = DEFAULT_INTENT_KEYWORDS.copy()
        self._frustration_signals = DEFAULT_FRUSTRATION_SIGNALS.copy()
        self.reload_rules()

    def reload_rules(self) -> None:
        """Safely load rules from data/fallback_rules.json."""
        with self._lock:
            try:
                # Ensure the parent directory exists
                self._rules_path.parent.mkdir(parents=True, exist_ok=True)
                
                if not self._rules_path.exists():
                    # Seed file with defaults
                    data = {
                        "_INTENT_KEYWORDS": DEFAULT_INTENT_KEYWORDS,
                        "_FRUSTRATION_SIGNALS": DEFAULT_FRUSTRATION_SIGNALS,
                    }
                    self._rules_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    logger.info("Seeded fallback rules at %s", self._rules_path)
                else:
                    data = json.loads(self._rules_path.read_text(encoding="utf-8"))
                    self._intent_keywords = data.get("_INTENT_KEYWORDS", DEFAULT_INTENT_KEYWORDS).copy()
                    self._frustration_signals = data.get("_FRUSTRATION_SIGNALS", DEFAULT_FRUSTRATION_SIGNALS).copy()
                    # Ensure values are correct types
                    self._frustration_signals = {k: float(v) for k, v in self._frustration_signals.items()}
            except Exception as e:
                logger.warning("Failed to load fallback rules from %s, using in-memory defaults. Error: %s", self._rules_path, e)

    def save_rules(self) -> None:
        """Write the current in-memory rules back to data/fallback_rules.json."""
        with self._lock:
            try:
                data = {
                    "_INTENT_KEYWORDS": self._intent_keywords,
                    "_FRUSTRATION_SIGNALS": self._frustration_signals,
                }
                self._rules_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                logger.info("Saved fallback rules to %s", self._rules_path)
            except Exception as e:
                logger.error("Failed to save fallback rules to %s. Error: %s", self._rules_path, e)

    def add_rule(self, pattern: str, label: str) -> None:
        """Dynamically add or update an intent rule and save it."""
        self._intent_keywords[pattern] = label
        self.save_rules()

    def add_frustration_signal(self, pattern: str, score: float) -> None:
        """Dynamically add or update a frustration signal and save it."""
        self._frustration_signals[pattern] = score
        self.save_rules()

    def extract(self, text: str) -> dict:
        lower = text.lower()

        intent_label = "unknown_ambient_activity"
        # Since Python 3.7 dict preserves insertion order, order of matching is predictable.
        with self._lock:
            intent_keywords = self._intent_keywords.copy()
            frustration_signals = self._frustration_signals.copy()

        for pattern, label in intent_keywords.items():
            try:
                if re.search(pattern, lower):
                    intent_label = label
                    break
            except re.error as e:
                logger.warning("Invalid regex pattern in fallback rules: %s. Error: %s", pattern, e)

        frustration = 0.0
        for pattern, score in frustration_signals.items():
            try:
                if re.search(pattern, lower):
                    frustration = max(frustration, score)
            except re.error as e:
                logger.warning("Invalid regex pattern in frustration signals: %s. Error: %s", pattern, e)

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
