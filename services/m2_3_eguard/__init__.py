"""M2.3 Eguard Cryptographic Filter

SPEC: docs/modules/M2_3_eguard_crypto_filter_SPEC.md v1.1
[R07: §5 Eguard] prevent embedding inversion attacks via discrete text masking
[R02: §架構安全性 DRIFT] block prompt injection at system boundary
"""
from .drift import DriftShield
from .exceptions import InjectionDetectedException
from .filter import EguardFilter
from .schema import RawTextPayload, SanitizedPayload

__all__ = [
    "EguardFilter",
    "DriftShield",
    "SanitizedPayload",
    "RawTextPayload",
    "InjectionDetectedException",
]
