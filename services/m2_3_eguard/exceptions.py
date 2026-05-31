"""M2.3 InjectionDetectedException

SPEC: docs/modules/M2_3_eguard_crypto_filter_SPEC.md v1.1 §7.5
anti-pattern: NEVER store raw payload in the exception -- only payload_hash.
Reason: log analysis tools or LLMs processing logs could trigger second-order injection
(log poisoning attack).
"""

from __future__ import annotations

import hashlib


class InjectionDetectedException(Exception):
    """Raised when DRIFT detects a prompt injection attempt.

    Only carries payload_hash (SHA-256) -- never the original plaintext.
    """

    def __init__(self, payload: str, pattern: str | None = None) -> None:
        self.payload_hash = hashlib.sha256(payload.encode()).hexdigest()
        self.pattern = pattern  # the heuristic keyword that triggered detection (not plaintext)
        super().__init__(
            f"EGUARD_BLOCK | hash={self.payload_hash} | pattern={self.pattern}"
        )
