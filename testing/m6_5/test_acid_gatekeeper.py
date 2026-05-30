"""
M6.5 -- ACID Transaction Gatekeeper acceptance tests

SPEC: docs/modules/M6_5_acid_gatekeeper_SPEC.md
Risk: RISK-01 (XP blocked for draft), RISK-07 (edge ZPD blocks stake)
Research:
  [R08 §六.1] IKEA effect: is_reviewed=True gates XP
  [R01 §α-DPO] stake refund must be atomic

Tests run in-memory against the XPGatekeeper service layer.
No live DB required -- gatekeeper accepts an injected session-like interface.
"""
import uuid
from dataclasses import dataclass, field
from datetime import date

import pytest

# ---------------------------------------------------------------------------
# In-memory test doubles
# ---------------------------------------------------------------------------

@dataclass
class FakeReflection:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    role_id: uuid.UUID = field(default_factory=uuid.uuid4)
    reflection_date: date = field(default_factory=date.today)
    ai_description: str = "VS Code 3h Rust"
    is_draft: bool = True
    is_reviewed: bool = False
    xp_settled: bool = False
    user_feeling: str | None = None
    user_action_plan: str | None = None
    earned_xp: int = 0
    xp_settled_at: object | None = None


@dataclass
class FakeUser:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    current_xp: int = 0


@dataclass
class FakeLedgerEntry:
    user_id: uuid.UUID
    amount: int
    xp_type: str
    reason: str
    source_module: str
    reflection_id: uuid.UUID | None = None
    role_id: uuid.UUID | None = None


@dataclass
class FakeTask:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    zpd_zone: str = "comfortable"  # "comfortable" | "proximal" | "edge"
    user_estimated_success: float = 0.8


class InMemoryStore:
    """Simple in-memory store used as the gatekeeper's session."""

    def __init__(self):
        self.reflections: dict[uuid.UUID, FakeReflection] = {}
        self.users: dict[uuid.UUID, FakeUser] = {}
        self.ledger: list[FakeLedgerEntry] = []
        self.tasks: dict[uuid.UUID, FakeTask] = {}
        self._locked: set[uuid.UUID] = set()  # simulates SELECT FOR UPDATE

    def add_reflection(self, r: FakeReflection) -> None:
        self.reflections[r.id] = r

    def add_user(self, u: FakeUser) -> None:
        self.users[u.id] = u

    def add_task(self, t: FakeTask) -> None:
        self.tasks[t.id] = t

    def latest_ledger(self, user_id: uuid.UUID) -> FakeLedgerEntry | None:
        entries = [e for e in self.ledger if e.user_id == user_id]
        return entries[-1] if entries else None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def draft_reflection(store):
    r = FakeReflection(is_draft=True, is_reviewed=False)
    store.add_reflection(r)
    return r


@pytest.fixture
def reviewed_reflection(store):
    r = FakeReflection(
        is_draft=False,
        is_reviewed=True,
        user_feeling="OK",
        user_action_plan="繼續",
    )
    store.add_reflection(r)
    return r


@pytest.fixture
def user(store):
    u = FakeUser(current_xp=0)
    store.add_user(u)
    return u


@pytest.fixture
def rich_user(store):
    u = FakeUser(current_xp=200)
    store.add_user(u)
    return u


@pytest.fixture
def safe_task(store):
    t = FakeTask(zpd_zone="proximal", user_estimated_success=0.8)
    store.add_task(t)
    return t


@pytest.fixture
def edge_task(store):
    t = FakeTask(zpd_zone="edge", user_estimated_success=0.4)
    store.add_task(t)
    return t


def make_gatekeeper(store):
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    return XPGatekeeper(store)


# ---------------------------------------------------------------------------
# Earned XP settlement tests
# ---------------------------------------------------------------------------

class TestEarnedXPSettlement:
    def test_xp_blocked_for_draft(self, store, user, draft_reflection):
        """AC-1: [RISK-01] draft reflection must block XP settlement."""
        gk = make_gatekeeper(store)
        result = gk.settle_earned_xp(
            reflection_id=draft_reflection.id,
            user_id=user.id,
            amount=50,
        )
        assert result.success is False
        assert result.error_code == "GATEKEEPER_001"
        assert user.current_xp == 0

    def test_xp_granted_after_review(self, store, user, reviewed_reflection):
        """AC-2: [RISK-01] approved reflection grants XP atomically."""
        gk = make_gatekeeper(store)
        result = gk.settle_earned_xp(
            reflection_id=reviewed_reflection.id,
            user_id=user.id,
            amount=50,
        )
        assert result.success is True
        assert user.current_xp == 50
        assert reviewed_reflection.xp_settled is True
        assert reviewed_reflection.earned_xp == 50
        # Ledger entry must exist
        entry = store.latest_ledger(user.id)
        assert entry is not None
        assert entry.amount == 50
        assert entry.xp_type == "earned"
        assert entry.source_module == "M4.5"

    def test_no_double_settlement(self, store, user, reviewed_reflection):
        """AC-3: same reflection cannot be settled twice."""
        gk = make_gatekeeper(store)
        gk.settle_earned_xp(reviewed_reflection.id, user.id, 50)
        result = gk.settle_earned_xp(reviewed_reflection.id, user.id, 50)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_002"
        assert user.current_xp == 50  # unchanged after second attempt

    def test_xp_blocked_missing_user_feeling(self, store, user):
        """AC-1b: [RISK-01] reviewed but empty user_feeling still blocks XP."""
        r = FakeReflection(
            is_draft=False, is_reviewed=True, user_feeling=None, user_action_plan="OK"
        )
        store.add_reflection(r)
        gk = make_gatekeeper(store)
        result = gk.settle_earned_xp(r.id, user.id, 50)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_001"

    def test_reflection_not_found(self, store, user):
        """AC: non-existent reflection returns GATEKEEPER_000."""
        gk = make_gatekeeper(store)
        result = gk.settle_earned_xp(uuid.uuid4(), user.id, 50)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_000"

    def test_xp_uses_relative_increment(self, store, user, reviewed_reflection):
        """AC: XP update must use relative increment (+amount), not absolute overwrite."""
        user.current_xp = 100
        gk = make_gatekeeper(store)
        gk.settle_earned_xp(reviewed_reflection.id, user.id, 50)
        assert user.current_xp == 150  # 100 + 50, not overwritten to 50


# ---------------------------------------------------------------------------
# XP staking tests
# ---------------------------------------------------------------------------

class TestXPStaking:
    def test_stake_blocked_for_edge_zpd(self, store, rich_user, edge_task):
        """AC-5: [RISK-07] edge ZPD task must be rejected."""
        gk = make_gatekeeper(store)
        result = gk.stake_xp(user_id=rich_user.id, task_id=edge_task.id, amount=100)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_003"

    def test_stake_deducts_and_ledger(self, store, rich_user, safe_task):
        """AC-6: successful stake deducts XP and writes ledger entry."""
        gk = make_gatekeeper(store)
        result = gk.stake_xp(user_id=rich_user.id, task_id=safe_task.id, amount=100)
        assert result.success is True
        assert rich_user.current_xp == 100  # 200 - 100
        entry = store.latest_ledger(rich_user.id)
        assert entry is not None
        assert entry.amount == -100
        assert entry.xp_type == "staked"

    def test_insufficient_xp_blocks_stake(self, store, user, safe_task):
        """AC-7: stake rejected when user has insufficient XP."""
        user.current_xp = 50
        gk = make_gatekeeper(store)
        result = gk.stake_xp(user_id=user.id, task_id=safe_task.id, amount=100)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_004"
        assert user.current_xp == 50  # unchanged


# ---------------------------------------------------------------------------
# Gacha transaction tests
# ---------------------------------------------------------------------------

class TestGachaTransaction:
    def test_gacha_deducts_xp(self, store, rich_user):
        """AC-8: gacha deducts XP and produces a reward."""
        gk = make_gatekeeper(store)
        result = gk.deduct_xp_for_gacha(user_id=rich_user.id, cost_xp=30)
        assert result.success is True
        assert rich_user.current_xp == 170  # 200 - 30
        assert result.reward is not None

    def test_gacha_rollback_on_reward_failure(self, store, rich_user):
        """AC-9: if reward generation fails, XP is rolled back."""
        gk = make_gatekeeper(store)
        result = gk.deduct_xp_for_gacha(
            user_id=rich_user.id, cost_xp=30, force_reward_failure=True
        )
        assert result.success is False
        assert result.error_code == "GATEKEEPER_005"
        assert rich_user.current_xp == 200  # rolled back

    def test_gacha_insufficient_xp(self, store, user):
        """AC: gacha rejects when XP insufficient."""
        user.current_xp = 10
        gk = make_gatekeeper(store)
        result = gk.deduct_xp_for_gacha(user_id=user.id, cost_xp=30)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_004"
        assert user.current_xp == 10  # unchanged


# ---------------------------------------------------------------------------
# Error code completeness test
# ---------------------------------------------------------------------------

class TestErrorCodes:
    def test_all_error_codes_defined(self):
        """AC: all documented error codes must be defined in the module."""
        from services.m6_5_acid_gatekeeper.gatekeeper import GATEKEEPER_CODES
        expected = {
            "GATEKEEPER_000", "GATEKEEPER_001", "GATEKEEPER_002",
            "GATEKEEPER_003", "GATEKEEPER_004", "GATEKEEPER_005",
        }
        assert expected.issubset(set(GATEKEEPER_CODES.keys()))
