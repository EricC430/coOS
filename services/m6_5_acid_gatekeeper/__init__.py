"""
M6.5 -- ACID Transaction Gatekeeper

SPEC: docs/modules/M6_5_acid_gatekeeper_SPEC.md
Risk mitigation: RISK-01 (XP gated by is_reviewed), RISK-07 (edge ZPD blocks stake)
Research: [R08 §六.1] IKEA effect, [R01 §alpha-DPO] atomic refund
"""
from .gatekeeper import GATEKEEPER_CODES, TransactionResult, XPGatekeeper

__all__ = ["XPGatekeeper", "TransactionResult", "GATEKEEPER_CODES"]
# v1.1: settle_segment_xp() is the new primary API (segment-level XP settlement)
