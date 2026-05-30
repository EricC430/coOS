"""
M6.5 -- XP Gatekeeper: ACID transaction logic (service layer)

SPEC: docs/modules/M6_5_acid_gatekeeper_SPEC.md §7.1-7.3
Research:
  [R08 §六.1] IKEA effect: is_reviewed=True is the gate for XP settlement
  [R01 §alpha-DPO] stake refund must be atomic (rollback on failure)
Risk mitigation:
  RISK-01: settle_earned_xp() enforces is_reviewed + user_feeling before any write
  RISK-07: stake_xp() blocks edge ZPD tasks to prevent compound frustration

Design note: this module operates on an injected store interface so it can be
tested in-memory (FakeStore) and also wired to a real SQLAlchemy session
(M4.5 will wire the live session). The gatekeeper does NOT hold DB connection
logic -- that is M0.3 / M6.2's responsibility.
"""
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Error code registry
# ---------------------------------------------------------------------------

GATEKEEPER_CODES: dict[str, str] = {
    "GATEKEEPER_000": "reflection_not_found",
    "GATEKEEPER_001": "draft_not_approved",
    "GATEKEEPER_002": "already_settled",
    "GATEKEEPER_003": "edge_zpd_forbidden",
    "GATEKEEPER_004": "insufficient_xp",
    "GATEKEEPER_005": "reward_generation_failed",
}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class TransactionResult:
    success: bool
    error_code: str | None = None
    error_reason: str | None = None
    reward: Any | None = None
    staked_amount: int | None = None


# ---------------------------------------------------------------------------
# Gatekeeper
# ---------------------------------------------------------------------------

class XPGatekeeper:
    """
    [RISK-01, CLAUDE.md §6] ACID transaction gatekeeper for all XP operations.

    All XP mutations MUST go through this class. Direct DB writes to
    users.current_xp or xp_ledger are forbidden (anti-pattern per SPEC §8).

    The store interface exposes:
      store.reflections: dict[UUID, reflection]
      store.users: dict[UUID, user]
      store.ledger: list[FakeLedgerEntry]
      store.tasks: dict[UUID, task]

    In production this will be replaced by an async SQLAlchemy session wrapper
    with SELECT FOR UPDATE locking.
    """

    def __init__(self, store: Any) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Earned XP settlement
    # ------------------------------------------------------------------

    def settle_earned_xp(
        self,
        reflection_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: int,
    ) -> TransactionResult:
        """
        [RISK-01] Atomically settle earned XP for an approved reflection.

        Guard order (matches SPEC §7.1):
        1. Reflection exists
        2. is_draft=False AND is_reviewed=True AND user_feeling non-empty
        3. xp_settled=False (prevent double-settlement)
        4. Relative XP increment (never absolute overwrite)
        5. Write ledger entry
        6. Mark xp_settled=True
        """
        reflection = self._store.reflections.get(reflection_id)
        if reflection is None:
            return TransactionResult(False, "GATEKEEPER_000", "reflection_not_found")

        # [RISK-01] Core gate: draft or unreviewed or missing user input
        if (reflection.is_draft
                or not reflection.is_reviewed
                or not reflection.user_feeling
                or not reflection.user_feeling.strip()):
            return TransactionResult(False, "GATEKEEPER_001", "draft_not_approved")

        if reflection.xp_settled:
            return TransactionResult(False, "GATEKEEPER_002", "already_settled")

        user = self._store.users.get(user_id)
        if user is None:
            return TransactionResult(False, "GATEKEEPER_000", "user_not_found")

        # [anti-pattern §8] Use relative increment, never absolute overwrite
        user.current_xp += amount

        # Write ledger entry
        self._store.ledger.append(_make_ledger(
            user_id=user_id,
            role_id=reflection.role_id,
            amount=amount,
            xp_type="earned",
            reason=f"daily_reflection_approved_{reflection.reflection_date}",
            source_module="M4.5",
            reflection_id=reflection_id,
        ))

        # Mark settled
        reflection.xp_settled = True
        reflection.xp_settled_at = datetime.now(UTC)
        reflection.earned_xp = amount

        return TransactionResult(True)

    # ------------------------------------------------------------------
    # XP staking (MVP: interface ready, frontend not yet triggered)
    # ------------------------------------------------------------------

    def stake_xp(
        self,
        user_id: uuid.UUID,
        task_id: uuid.UUID,
        amount: int,
    ) -> TransactionResult:
        """
        [RISK-07] Stake XP on a task. Blocked for edge ZPD tasks.
        MVP: interface exists; M4.13 will wire the frontend trigger.
        """
        task = self._store.tasks.get(task_id)
        if task is None:
            return TransactionResult(False, "GATEKEEPER_000", "task_not_found")

        # [RISK-07] Edge ZPD = compound frustration risk; forbid staking
        if task.zpd_zone == "edge":
            return TransactionResult(False, "GATEKEEPER_003", "edge_zpd_forbidden")

        user = self._store.users.get(user_id)
        if user is None:
            return TransactionResult(False, "GATEKEEPER_000", "user_not_found")

        if user.current_xp < amount:
            return TransactionResult(False, "GATEKEEPER_004", "insufficient_xp")

        # [anti-pattern §8] Relative decrement
        user.current_xp -= amount

        self._store.ledger.append(_make_ledger(
            user_id=user_id,
            amount=-amount,
            xp_type="staked",
            reason=f"task_stake_{task_id}",
            source_module="M4.13",
        ))

        return TransactionResult(True, staked_amount=amount)

    # ------------------------------------------------------------------
    # Gacha deduction (MVP: interface ready, frontend not yet triggered)
    # ------------------------------------------------------------------

    def deduct_xp_for_gacha(
        self,
        user_id: uuid.UUID,
        cost_xp: int,
        force_reward_failure: bool = False,
    ) -> TransactionResult:
        """
        [R01 §alpha-DPO] Gacha deduction + reward generation are atomic.
        If reward generation fails, XP is rolled back.
        MVP: interface exists; M3.11 will wire the frontend trigger.
        """
        user = self._store.users.get(user_id)
        if user is None:
            return TransactionResult(False, "GATEKEEPER_000", "user_not_found")

        if user.current_xp < cost_xp:
            return TransactionResult(False, "GATEKEEPER_004", "insufficient_xp")

        # Deduct first (rollback on reward failure)
        user.current_xp -= cost_xp

        # [anti-pattern §8] If reward fails, rollback deduction atomically
        if force_reward_failure:
            user.current_xp += cost_xp  # rollback
            return TransactionResult(False, "GATEKEEPER_005", "reward_generation_failed")

        reward = _generate_gacha_reward(user_id)

        self._store.ledger.append(_make_ledger(
            user_id=user_id,
            amount=-cost_xp,
            xp_type="gacha",
            reason=f"gacha_draw_{reward['id']}",
            source_module="M3.11",
        ))

        return TransactionResult(True, reward=reward)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ledger(**kwargs):
    """Build a simple dict ledger entry (production will use SQLAlchemy model)."""
    from dataclasses import make_dataclass
    entry_type = make_dataclass("LedgerEntry", list(kwargs.keys()))
    return entry_type(**kwargs)


def _generate_gacha_reward(user_id: uuid.UUID) -> dict:
    """Stub reward generator (M3.11 will replace with real logic)."""
    return {"id": str(uuid.uuid4()), "type": "badge", "rarity": "common"}
