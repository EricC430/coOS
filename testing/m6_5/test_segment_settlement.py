"""
M6.5 v1.1 -- Segment-level XP settlement tests

SPEC: docs/modules/M6_5_acid_gatekeeper_SPEC.md v1.1
Risk: RISK-01 (XP gated), RISK-13 (soft-delete), RISK-14 (lifetime_xp sync)
Research:
  [R08 §六.1] IKEA effect at segment level
  [R01 §alpha-DPO] atomic refund
"""
import uuid
from dataclasses import dataclass, field
from datetime import date

import pytest

# ---------------------------------------------------------------------------
# In-memory test doubles (v1.1 -- adds segments dict + lifetime_xp)
# ---------------------------------------------------------------------------

@dataclass
class FakeReflection:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    role_id: uuid.UUID = field(default_factory=uuid.uuid4)
    reflection_date: date = field(default_factory=date.today)
    is_completed: bool = False


@dataclass
class FakeSegment:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    reflection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    is_draft: bool = True
    is_reviewed: bool = False
    xp_settled: bool = False
    user_feeling: str | None = None
    user_action_plan: str | None = None
    earned_xp: int = 0
    xp_settled_at: object | None = None
    is_active: bool = True


@dataclass
class FakeUser:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    current_xp: int = 0
    lifetime_xp: int = 0  # v1.1: RISK-14


class InMemoryStore:
    def __init__(self):
        self.reflections: dict = {}
        self.segments: dict = {}
        self.users: dict = {}
        self.ledger: list = []
        self.tasks: dict = {}

    def add_reflection(self, r):
        self.reflections[r.id] = r

    def add_segment(self, s):
        self.segments[s.id] = s

    def add_user(self, u):
        self.users[u.id] = u

    def add_task(self, t):
        self.tasks[t.id] = t

    def latest_ledger(self, user_id):
        entries = [e for e in self.ledger if e.user_id == user_id]
        return entries[-1] if entries else None


@dataclass
class FakeTask:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    zpd_zone: str = "proximal"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def reflection(store):
    r = FakeReflection()
    store.add_reflection(r)
    return r


@pytest.fixture
def approved_segment(store, reflection):
    s = FakeSegment(
        reflection_id=reflection.id,
        is_draft=False, is_reviewed=True,
        user_feeling="Great session", is_active=True,
    )
    store.add_segment(s)
    return s


@pytest.fixture
def draft_segment(store, reflection):
    s = FakeSegment(reflection_id=reflection.id, is_draft=True, is_reviewed=False)
    store.add_segment(s)
    return s


@pytest.fixture
def user(store):
    u = FakeUser(current_xp=0, lifetime_xp=0)
    store.add_user(u)
    return u


@pytest.fixture
def rich_user(store):
    u = FakeUser(current_xp=200, lifetime_xp=500)
    store.add_user(u)
    return u


def make_gk(store):
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    return XPGatekeeper(store)


# ---------------------------------------------------------------------------
# TestSegmentXPSettlement
# ---------------------------------------------------------------------------

class TestSegmentXPSettlement:
    def test_xp_blocked_for_draft_segment(self, store, user, draft_segment):
        """[RISK-01] draft segment must block XP settlement."""
        gk = make_gk(store)
        result = gk.settle_segment_xp(draft_segment.id, user.id, 50)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_001"
        assert user.current_xp == 0
        assert user.lifetime_xp == 0

    def test_xp_granted_for_approved_segment(self, store, user, approved_segment):
        """[RISK-01] approved segment grants XP."""
        gk = make_gk(store)
        result = gk.settle_segment_xp(approved_segment.id, user.id, 50)
        assert result.success is True
        assert user.current_xp == 50

    def test_lifetime_xp_incremented_with_current(self, store, user, approved_segment):
        """[RISK-14] lifetime_xp must increase alongside current_xp on earn."""
        gk = make_gk(store)
        gk.settle_segment_xp(approved_segment.id, user.id, 50)
        assert user.current_xp == 50
        assert user.lifetime_xp == 50

    def test_lifetime_xp_not_decremented_by_gacha(self, store, rich_user):
        """[RISK-14] gacha deduction does NOT affect lifetime_xp."""
        gk = make_gk(store)
        lifetime_before = rich_user.lifetime_xp
        gk.deduct_xp_for_gacha(user_id=rich_user.id, cost_xp=30)
        assert rich_user.current_xp == 170
        assert rich_user.lifetime_xp == lifetime_before  # unchanged

    def test_no_double_settlement(self, store, user, approved_segment):
        """AC-3: same segment cannot be settled twice."""
        gk = make_gk(store)
        gk.settle_segment_xp(approved_segment.id, user.id, 50)
        result = gk.settle_segment_xp(approved_segment.id, user.id, 50)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_002"
        assert user.current_xp == 50  # unchanged

    def test_soft_deleted_segment_blocked(self, store, user, reflection):
        """[RISK-13] soft-deleted segment (is_active=False) cannot settle XP."""
        soft_seg = FakeSegment(
            reflection_id=reflection.id,
            is_draft=False, is_reviewed=True,
            user_feeling="OK", is_active=False,
        )
        store.add_segment(soft_seg)
        gk = make_gk(store)
        result = gk.settle_segment_xp(soft_seg.id, user.id, 50)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_000"
        assert user.current_xp == 0

    def test_xp_relative_increment(self, store, user, approved_segment):
        """[anti-pattern §8] XP uses relative increment, not absolute overwrite."""
        user.current_xp = 100
        user.lifetime_xp = 200
        gk = make_gk(store)
        gk.settle_segment_xp(approved_segment.id, user.id, 50)
        assert user.current_xp == 150   # 100 + 50
        assert user.lifetime_xp == 250  # 200 + 50

    def test_ledger_entry_created_with_segment_id(self, store, user, approved_segment):
        """Ledger entry must reference the segment_id for statistics."""
        gk = make_gk(store)
        gk.settle_segment_xp(approved_segment.id, user.id, 50)
        entry = store.latest_ledger(user.id)
        assert entry is not None
        assert entry.amount == 50
        assert entry.xp_type == "earned"
        assert entry.segment_id == approved_segment.id

    def test_segment_marked_xp_settled(self, store, user, approved_segment):
        """After settlement segment.xp_settled=True and earned_xp set."""
        gk = make_gk(store)
        gk.settle_segment_xp(approved_segment.id, user.id, 75)
        assert approved_segment.xp_settled is True
        assert approved_segment.earned_xp == 75
        assert approved_segment.xp_settled_at is not None

    def test_segment_not_found_returns_000(self, store, user):
        """Non-existent segment returns GATEKEEPER_000."""
        gk = make_gk(store)
        result = gk.settle_segment_xp(uuid.uuid4(), user.id, 50)
        assert result.success is False
        assert result.error_code == "GATEKEEPER_000"


# ---------------------------------------------------------------------------
# TestLifetimeXPInvariant
# ---------------------------------------------------------------------------

class TestLifetimeXPInvariant:
    def test_earn_then_spend_preserves_lifetime(self, store, rich_user):
        """[RISK-14] lifetime_xp reflects total earned, never reflects spending."""
        reflection = FakeReflection(user_id=rich_user.id)
        store.add_reflection(reflection)
        seg = FakeSegment(
            reflection_id=reflection.id,
            is_draft=False, is_reviewed=True,
            user_feeling="Focused", is_active=True,
        )
        store.add_segment(seg)
        gk = make_gk(store)

        # Earn 60 XP
        gk.settle_segment_xp(seg.id, rich_user.id, 60)
        assert rich_user.current_xp == 260    # 200 + 60
        assert rich_user.lifetime_xp == 560   # 500 + 60

        # Spend 30 XP on Gacha
        gk.deduct_xp_for_gacha(user_id=rich_user.id, cost_xp=30)
        assert rich_user.current_xp == 230    # 260 - 30
        assert rich_user.lifetime_xp == 560   # still 560 -- never decreases

    def test_stake_does_not_affect_lifetime(self, store, rich_user):
        """[RISK-14] XP staking reduces current_xp but NOT lifetime_xp."""
        task = FakeTask(zpd_zone="proximal")
        store.add_task(task)
        gk = make_gk(store)
        lifetime_before = rich_user.lifetime_xp

        gk.stake_xp(user_id=rich_user.id, task_id=task.id, amount=50)
        assert rich_user.current_xp == 150  # 200 - 50
        assert rich_user.lifetime_xp == lifetime_before  # unchanged
