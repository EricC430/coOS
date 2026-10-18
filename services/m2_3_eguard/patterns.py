"""M2.3 PII detection patterns -- pre-compiled regex for performance

SPEC: docs/modules/M2_3_eguard_crypto_filter_SPEC.md v1.1 §7.3
[R07: §5 Eguard] discrete text masking as engineering adaptation of mutual-information optimization

anti-pattern: never use un-compiled regex or without timeout (ReDoS risk).
Each pattern has a 10ms timeout enforced in filter.py.
"""

from __future__ import annotations

import re

# [D6] Alphanumeric boundaries instead of \b: Python treats CJK as \w, so \b never
# fires between a Chinese character and a letter/digit ("身分證A123456789").
_L = r"(?<![A-Za-z0-9])"
_R = r"(?![A-Za-z0-9])"

PII_PATTERNS: dict[str, re.Pattern] = {
    "EMAIL": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    "IPV4": re.compile(
        _L + r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)" + _R
    ),
    "API_KEY_GOOGLE": re.compile(r"(?<![A-Za-z0-9_-])AIzaSy[A-Za-z0-9_-]{33}(?![A-Za-z0-9_-])"),
    # 13-16 digits, single space/dash separators allowed. Matches are only
    # candidates: filter.py masks them only if they pass the Luhn check.
    "CREDIT_CARD": re.compile(_L + r"\d(?:[ -]?\d){12,15}" + _R),
    "TAIWAN_ID": re.compile(_L + r"[A-Z][12]\d{8}" + _R),
    "GENERIC_SECRET": re.compile(
        r"(?i)(?:secret|token|password|passwd|api[_-]?key)\s*[=:]\s*\S+"
    ),
}

LOCALHOST_PATTERN = re.compile(_L + r"127\.0\.0\.1" + _R + "|" + _L + r"localhost" + _R)
