"""
M4.13.1 — Stake Engine (XP Staking Business Logic)

SPEC: docs/modules/M3_7_community_ui_SPEC.md §7.4 (POST /api/m6_6/stakes)
RISK-07: Dual gating — zpd_zone != 'edge' AND success_rate >= 0.70
Delegates actual XP hold/settle/forfeit to M6.5 ACID Gatekeeper.
"""
import logging
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StakeGateResult:
    allowed: bool
    reason: str = ""


# Stub for M4.8 implicit state (焦慮門禁) — safe default per plan
def _get_implicit_state() -> dict[str, Any]:
    """
    [RISK-09] M4.8 stub — returns safe default.
    When M4.8 is implemented, this will read from the real implicit state module.
    """
    return {"label": "normal", "confidence": 0.5}


def can_stake_on_task(
    xp_balance: int,
    stake_amount: int,
    zpd_zone: str = "comfort",
    success_rate: float = 0.80,
) -> StakeGateResult:
    """
    [RISK-07] Dual gating for XP stake eligibility:
      1. zpd_zone must NOT be 'edge' (compound frustration risk)
      2. success_rate must be >= 0.70 (high-confidence tasks only)
      3. xp_balance must be >= stake_amount
      4. [RISK-09] Implicit state must not be 'anxious'
    """
    # Gate 1: ZPD zone check
    if zpd_zone == "edge":
        return StakeGateResult(
            allowed=False,
            reason="質押被拒：此任務位於 ZPD 邊緣區，風險過高不允許質押。",
        )

    # Gate 2: Success rate check
    if success_rate < 0.70:
        return StakeGateResult(
            allowed=False,
            reason=f"質押被拒：任務成功率 {success_rate:.0%} 低於門檻 70%。",
        )

    # Gate 3: Balance check
    if xp_balance < stake_amount:
        return StakeGateResult(
            allowed=False,
            reason=f"質押被拒：XP 餘額不足（需要 {stake_amount}，目前 {xp_balance}）。",
        )

    # Gate 4: Implicit state check (M4.8 stub)
    implicit = _get_implicit_state()
    if implicit.get("label") == "anxious" and implicit.get("confidence", 0) > 0.70:
        return StakeGateResult(
            allowed=False,
            reason="質押被拒：偵測到焦慮狀態，建議先休息再嘗試。",
        )

    return StakeGateResult(allowed=True, reason="質押允許")
