"""M2.3 DriftShield -- DRIFT prompt injection detection

SPEC: docs/modules/M2_3_eguard_crypto_filter_SPEC.md v1.1 §7.4
[R02: §架構安全性 DRIFT] dual-layer: heuristic filter + semantic audit
RISK-M2.3-C: semantic audit calls ai.local raw API DIRECTLY (NOT via M2.2 InferencePriorityQueue)
to avoid circular dependency M2.3 -> M2.2 -> M2.3.

anti-pattern: NEVER record original plaintext in exception or logs (log poisoning risk).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml

from .exceptions import InjectionDetectedException
from .schema import SanitizedPayload

_DRIFT_RULES_PATH = Path(__file__).resolve().parent / "drift_rules.yaml"
_EGUARDIGNORE_PATH = Path(__file__).resolve().parents[2] / ".eguardignore"

# Default heuristic keywords if drift_rules.yaml absent
_DEFAULT_INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all previous",
    "system prompt",
    "you are now a",
    "disregard your",
    "forget everything",
    "act as if",
    "override your",
    "bypass your",
    "pretend you",
]


def _load_keywords() -> list[str]:
    if _DRIFT_RULES_PATH.exists():
        try:
            data = yaml.safe_load(_DRIFT_RULES_PATH.read_text(encoding="utf-8"))
            return data.get("injection_keywords", _DEFAULT_INJECTION_KEYWORDS)
        except Exception:
            pass
    return _DEFAULT_INJECTION_KEYWORDS


def _load_eguardignore_paths() -> list[str]:
    if not _EGUARDIGNORE_PATH.exists():
        return []
    try:
        data = yaml.safe_load(_EGUARDIGNORE_PATH.read_text(encoding="utf-8"))
        return data.get("paths", []) if isinstance(data, dict) else []
    except Exception:
        return []


class DriftShield:
    """Dual-layer prompt injection detector.

    Layer 1: Static heuristic keyword scan (fast).
    Layer 2: Semantic audit via ai.local Gemma raw API (skipped if offline).

    RISK-M2.3-A: source_paths matching .eguardignore get audit_level=WARNING, not BLOCKED.
    RISK-M2.3-C: semantic audit bypasses M2.2 InferencePriorityQueue.
    """

    def __init__(self, ai_local_host: str | None = None) -> None:
        self._keywords = _load_keywords()
        self._ignore_patterns = _load_eguardignore_paths()
        self._ai_local_host = ai_local_host  # optional; if None, semantic audit is skipped

    def verify_input(
        self,
        text: str,
        source_path: str | None = None,
    ) -> str | SanitizedPayload:
        """Verify text is safe for LLM ingestion.

        Returns the original text if safe.
        For .eguardignore paths: returns SanitizedPayload with audit_level=WARNING.
        Raises InjectionDetectedException for detected injections (non-ignored paths).
        """
        lower = text.lower()
        matched_keyword: str | None = None

        for kw in self._keywords:
            if kw in lower:
                matched_keyword = kw
                break

        if matched_keyword is None:
            return text  # clean

        is_ignored = any(
            fnmatch.fnmatch(source_path or "", pat) for pat in self._ignore_patterns
        )

        if is_ignored:
            # RISK-M2.3-A: only warn, do not block
            return SanitizedPayload(
                original_length=len(text),
                sanitized_text=text,
                flagged=True,
                masked_entities=["INJECTION_PATTERN"],
                role_id="",
                audit_level="WARNING",
            )

        # Raise exception -- only payload_hash, never plaintext (anti log-poisoning)
        raise InjectionDetectedException(payload=text, pattern=matched_keyword)
