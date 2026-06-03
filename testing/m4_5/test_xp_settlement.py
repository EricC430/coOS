"""
M4.5 Zero-Friction XP Settlement Engine -- test suite

SPEC: docs/modules/M4_5_xp_settlement_SPEC.md §6
Research: [R08 §六.1 IKEA] [R08 §五 意圖脫鉤] [R08 §四.2 微摩擦力]
Risk coverage:
  RISK-01 (no XP before is_reviewed + user_feeling + user_action_plan)
  RISK-14 (current_xp + lifetime_xp updated atomically; lifetime never decreases)
  RISK-13 (settled reflections never auto-rolled-back)

Design: the engine computes the XP amount (factors per SPEC §9) and delegates the
atomic write to the M6.5 XPGatekeeper. Tests wire a real XPGatekeeper over an
in-memory FakeStore so the full guard chain (RISK-01/14) is exercised end-to-end.
"""
from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_5_xp_settlement.ambient import calculate_ambient_xp  # noqa: E402
from m4_5_xp_settlement.engine import deduct_xp, settle  # noqa: E402
from m4_5_xp_settlement.zombie_cleanup import run_zombie_cleanup_cron  # noqa: E402
from m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper  # noqa: E402

# ---------------------------------------------------------------------------
# In-memory fakes
# ---------------------------------------------------------------------------

@dataclass
class FakeUser:
    id: uuid.UUID
    current_xp: int = 0
    lifetime_xp: int = 0


@dataclass
class FakeReflection:
    id: uuid.UUID
    role_id: uuid.UUID
    reflection_date: object = "2026-06-02"
    is_draft: bool = True
    is_reviewed: bool = False
    user_feeling: str | None = None
    user_action_plan: str | None = None
    user_learned: str | None = None
    activity_minutes: int = 0
    goal_aligned: bool = False
    xp_settled: bool = False
    xp_settled_at: datetime | None = None
    earned_xp: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class FakeStore:
    users: dict = field(default_factory=dict)
    reflections: dict = field(default_factory=dict)
    segments: dict = field(default_factory=dict)
    tasks: dict = field(default_factory=dict)
    ledger: list = field(default_factory=list)


def _setup(reflection: FakeReflection):
    user = FakeUser(id=uuid.uuid4())
    store = FakeStore()
    store.users[user.id] = user
    store.reflections[reflection.id] = reflection
    gatekeeper = XPGatekeeper(store)
    return user, store, gatekeeper


def _reflection(**kw) -> FakeReflection:
    return FakeReflection(id=uuid.uuid4(), role_id=uuid.uuid4(), **kw)


def _approved(**kw) -> FakeReflection:
    base = dict(
        is_draft=False, is_reviewed=True,
        user_feeling="ok", user_action_plan="ok",
    )
    base.update(kw)
    return _reflection(**base)


# ---------------------------------------------------------------------------
# M4.5.1 XP settlement gate (RISK-01)
# ---------------------------------------------------------------------------

class TestM4_5_1_XPSettlement:
    @pytest.mark.asyncio
    async def test_xp_blocked_for_draft(self):
        """[RISK-01] 草稿狀態下 XP 必不發放"""
        r = _reflection(is_draft=True, is_reviewed=False)
        user, _, gk = _setup(r)
        result = await settle(r, user, gatekeeper=gk)
        assert result.granted is False
        assert result.reason == "draft_not_approved"
        assert user.current_xp == 0

    @pytest.mark.asyncio
    async def test_xp_blocked_without_user_feeling(self):
        """[RISK-01] is_reviewed=true 但 user_feeling 為空 → 拒絕"""
        r = _reflection(is_draft=False, is_reviewed=True, user_feeling=None, user_action_plan="ok")
        user, _, gk = _setup(r)
        result = await settle(r, user, gatekeeper=gk)
        assert result.granted is False
        assert user.current_xp == 0

    @pytest.mark.asyncio
    async def test_xp_blocked_without_action_plan(self):
        """[RISK-01] user_action_plan 為空 → 拒絕"""
        r = _reflection(is_draft=False, is_reviewed=True, user_feeling="ok", user_action_plan=None)
        user, _, gk = _setup(r)
        result = await settle(r, user, gatekeeper=gk)
        assert result.granted is False
        assert user.current_xp == 0

    @pytest.mark.asyncio
    async def test_xp_granted_after_full_approval(self):
        """[R08 §六.1] 完整核准後 XP 發放"""
        r = _approved(activity_minutes=120)
        user, _, gk = _setup(r)
        result = await settle(r, user, gatekeeper=gk)
        assert result.granted is True
        assert result.amount > 0
        assert user.current_xp == result.amount

    @pytest.mark.asyncio
    async def test_xp_calculation_factors(self):
        """[決策] XP = 基礎分鐘數 + 目標對齊 1.5x + 學習筆記 +10 + 深思熟慮加成"""
        # 1. 基礎：120 分鐘 = 50 XP
        r_base = _approved(activity_minutes=120, user_learned=None, goal_aligned=False)
        u, _, gk = _setup(r_base)
        assert (await settle(r_base, u, gatekeeper=gk, approval_duration_seconds=0)).amount == 50

        # 2. 對齊目標：1.5x
        r_aligned = _approved(activity_minutes=120, user_learned=None, goal_aligned=True)
        u, _, gk = _setup(r_aligned)
        assert (await settle(r_aligned, u, gatekeeper=gk, approval_duration_seconds=0)).amount == 75

        # 3. 學習筆記：+10
        r_learned = _approved(
            activity_minutes=120, user_learned="學會了生命週期", goal_aligned=False
        )
        u, _, gk = _setup(r_learned)
        assert (await settle(r_learned, u, gatekeeper=gk, approval_duration_seconds=0)).amount == 60

        # 4. 深思熟慮加成：30 秒 (0.1 XP/s, +3)
        r_dur = _approved(activity_minutes=120, user_learned=None, goal_aligned=False)
        u, _, gk = _setup(r_dur)
        assert (await settle(r_dur, u, gatekeeper=gk, approval_duration_seconds=30)).amount == 53

    @pytest.mark.asyncio
    async def test_xp_settlement_is_idempotent(self):
        """重複結算同一反思不會重複發放"""
        r = _approved(activity_minutes=120)
        user, _, gk = _setup(r)
        await settle(r, user, gatekeeper=gk)
        xp_before = user.current_xp
        await settle(r, user, gatekeeper=gk)
        assert user.current_xp == xp_before

    @pytest.mark.asyncio
    async def test_both_xp_columns_updated(self):
        """[RISK-14] current_xp 與 lifetime_xp 同時更新"""
        r = _approved(activity_minutes=120)
        user, _, gk = _setup(r)
        await settle(r, user, gatekeeper=gk)
        assert user.current_xp > 0
        assert user.lifetime_xp == user.current_xp

    def test_lifetime_xp_never_decreases(self):
        """[RISK-14] 消費後 lifetime_xp 不減"""
        user = FakeUser(id=uuid.uuid4(), current_xp=100, lifetime_xp=100)
        deduct_xp(user, 30)
        assert user.current_xp == 70
        assert user.lifetime_xp == 100

    @pytest.mark.asyncio
    async def test_ledger_entry_created(self):
        """每次結算必產生 xp_ledger 記錄"""
        r = _approved(activity_minutes=120)
        user, store, gk = _setup(r)
        await settle(r, user, gatekeeper=gk)
        assert len(store.ledger) == 1
        entry = store.ledger[-1]
        assert entry.source_module == "M4.5"
        assert entry.xp_type == "earned"
        assert entry.amount > 0

    def test_ambient_xp_capped_at_5_percent(self):
        """[RISK-01] Ambient XP ≤ 每日總 XP 的 5%"""
        daily_earned = 100
        ambient = calculate_ambient_xp(daily_earned)
        assert ambient <= daily_earned * 0.05

    @pytest.mark.asyncio
    async def test_negative_activity_minimum_participation_reward(self):
        """活動極少時仍給最低參與獎勵 5 XP（不為負/不為零）"""
        r = _approved(activity_minutes=1)
        user, _, gk = _setup(r)
        result = await settle(r, user, gatekeeper=gk)
        assert result.amount == 5


# ---------------------------------------------------------------------------
# M4.5.2 Zombie draft cleanup
# ---------------------------------------------------------------------------

class TestM4_5_2_ZombieDraftCleanup:
    @pytest.mark.asyncio
    async def test_stale_drafts_deleted_after_configured_days(self):
        """[決策] 根據使用者配置天數（預設 7）自動淘汰未審草稿"""
        now = datetime.now(UTC)
        old = _reflection(is_draft=True, created_at=now - timedelta(days=4))
        recent = _reflection(is_draft=True, created_at=now - timedelta(days=2))
        store = FakeStore()
        store.reflections[old.id] = old
        store.reflections[recent.id] = recent

        deleted = await run_zombie_cleanup_cron(store, threshold_days=3, now=now)
        assert old.id in deleted
        assert recent.id not in deleted
        assert old.id not in store.reflections
        assert recent.id in store.reflections

    @pytest.mark.asyncio
    async def test_approved_reflections_never_deleted(self):
        """[決策][RISK-13] 已核准反思永不被殭屍清理刪除"""
        now = datetime.now(UTC)
        approved = _approved(created_at=now - timedelta(days=30))
        store = FakeStore()
        store.reflections[approved.id] = approved

        deleted = await run_zombie_cleanup_cron(store, threshold_days=7, now=now)
        assert approved.id not in deleted
        assert approved.id in store.reflections

    @pytest.mark.asyncio
    async def test_settled_reflection_never_deleted(self):
        """[RISK-13] 已結算反思不可被清理"""
        now = datetime.now(UTC)
        r = _reflection(is_draft=True, xp_settled=True, created_at=now - timedelta(days=30))
        store = FakeStore()
        store.reflections[r.id] = r
        deleted = await run_zombie_cleanup_cron(store, threshold_days=7, now=now)
        assert r.id not in deleted
        assert r.id in store.reflections
