"""M2.3 PII detection patterns -- pre-compiled regex for performance

SPEC: docs/modules/M2_3_eguard_crypto_filter_SPEC.md v1.1 §7.3
[R07: §5 Eguard] discrete text masking as engineering adaptation of mutual-information optimization

anti-pattern: never use un-compiled regex or without timeout (ReDoS risk).
Each pattern has a 10ms timeout enforced in filter.py.
"""

from __future__ import annotations

import re

PII_PATTERNS: dict[str, re.Pattern] = {
    "EMAIL": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "IPV4": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    ),
    "API_KEY_GOOGLE": re.compile(r"\bAIzaSy[A-Za-z0-9_-]{33}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "TAIWAN_ID": re.compile(r"\b[A-Z][12]\d{8}\b"),
    "GENERIC_SECRET": re.compile(
        r"(?i)(?:secret|token|password|passwd|api[_-]?key)\s*[=:]\s*\S+"
    ),
}

LOCALHOST_PATTERN = re.compile(r"\b127\.0\.0\.1\b|\blocalhost\b")
