"""
M4.11 Dynamic ZPD Gacha Pipeline
================================
Complies with Constitution Principle I (Three-Tier Privacy) and Principle II (Psychological Invariants).

Research citations:
  - [R01: ZONE 框架 §理論基礎] REJECT + GRAD mechanism for proximal development boundary
  - [R01: 多模態 BKT §動態追蹤] Bayesian Knowledge Tracing for capability and cognitive load
  - [R01: α-DPO, RISK-07] Zero-Staking invariant for compound frustration defense
  - [R08: 微摩擦 §IV.2] Self-attestation reflection before XP claim
  - [R09: 焦慮門禁 §3.3] Cognitive overload and anxiety safety retraction
"""

__version__ = "1.0.0"
__module__ = "M4.11"

from .schemas import (
    ChallengeStatus,
    CompleteChallengeRequest,
    DrawChallengeRequest,
    TaskDifficulty,
    TaskType,
    ZPDChallengeDTO,
)

__all__ = [
    "__version__",
    "__module__",
    "TaskType",
    "TaskDifficulty",
    "ChallengeStatus",
    "ZPDChallengeDTO",
    "DrawChallengeRequest",
    "CompleteChallengeRequest",
]
