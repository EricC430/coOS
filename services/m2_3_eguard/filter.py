"""M2.3 EguardFilter -- PII masking with .eguardignore support

SPEC: docs/modules/M2_3_eguard_crypto_filter_SPEC.md v1.1 §7.3, §7.6
[R07: §5 Eguard] discrete text masking prevents embedding inversion attacks
RISK-M2.3-A: .eguardignore paths only WARNING, never BLOCKED
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import yaml

from .patterns import LOCALHOST_PATTERN, PII_PATTERNS
from .schema import SanitizedPayload

_EGUARDIGNORE_PATH = Path(__file__).resolve().parents[2] / ".eguardignore"

_REPLACEMENT_MAP = {
    "EMAIL": "[REDACTED_EMAIL]",
    "IPV4": "[REDACTED_IP]",
    "API_KEY_GOOGLE": "[REDACTED_API_KEY]",
    "CREDIT_CARD": "[REDACTED_CARD]",
    "TAIWAN_ID": "[REDACTED_ID]",
    "GENERIC_SECRET": "[REDACTED_SECRET]",
}


def _load_eguardignore_paths() -> list[str]:
    if not _EGUARDIGNORE_PATH.exists():
        return []
    try:
        data = yaml.safe_load(_EGUARDIGNORE_PATH.read_text(encoding="utf-8"))
        return data.get("paths", []) if isinstance(data, dict) else []
    except Exception:
        return []


def _is_ignored(source_path: str | None, ignore_patterns: list[str]) -> bool:
    if not source_path:
        return False
    return any(fnmatch.fnmatch(source_path, pat) for pat in ignore_patterns)


class EguardFilter:
    """PII masking engine with context-aware false-positive mitigation.

    Reads .eguardignore from repo root; matched source_paths get audit_level=WARNING
    instead of BLOCKED.
    """

    def __init__(self) -> None:
        self._ignore_patterns = _load_eguardignore_paths()

    def mask_pii(
        self,
        text: str,
        role_id: str = "",
        source_path: str | None = None,
        is_code_context: bool = False,
    ) -> SanitizedPayload:
        """Scan and mask PII in text. Returns SanitizedPayload with role_id propagated."""
        masked = text
        masked_entities: list[str] = []
        flagged = False

        is_ignored = _is_ignored(source_path, self._ignore_patterns)

        for name, pattern in PII_PATTERNS.items():
            # RISK-M2.3-A: in code context, skip localhost/loopback IP masking
            if name == "IPV4" and is_code_context:
                if LOCALHOST_PATTERN.search(masked):
                    continue  # do not mask 127.0.0.1 in code

            if pattern.search(masked):
                replacement = _REPLACEMENT_MAP.get(name, f"[REDACTED_{name}]")
                masked = pattern.sub(replacement, masked)
                masked_entities.append(name)
                flagged = True

        if flagged and is_ignored:
            audit_level = "WARNING"
        elif flagged:
            audit_level = "BLOCKED"
        else:
            audit_level = "OK"

        return SanitizedPayload(
            original_length=len(text),
            sanitized_text=masked,
            flagged=flagged,
            masked_entities=masked_entities,
            role_id=role_id,
            audit_level=audit_level,
        )
