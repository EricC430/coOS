"""
M6.5 -- XPGatekeeper wired to the production LiveXPStore (services/main.py)

SPEC: docs/modules/M6_5_acid_gatekeeper_SPEC.md §6 AC-2
Risk: RISK-01 (XP only after approval), RISK-14 (current_xp + lifetime_xp)

AC-2 is covered in-memory by test_acid_gatekeeper.py. This file runs the same
check through the store that /api/m4_5/grant_xp actually builds, using a fake
async DB adapter (no sidecar, no real DB).
"""
import uuid

import pytest


class FakeAsyncDB:
    """Minimal AsyncDBAdapter stand-in: one approved segment, one user."""

    def __init__(self):
        self.executed: list[str] = []

    async def fetch_one(self, query, params=None):
        if "daily_reflection_segments" in query:
            return {
                "id": params["sid"],
                "reflection_id": None,
                "is_draft": 0,
                "is_reviewed": 1,
                "user_feeling": "focused",
                "xp_settled": 0,
            }
        if "FROM users" in query:
            return {"id": params["uid"], "current_xp": 0, "lifetime_xp": 0}
        return None

    async def execute(self, query, params=None):
        self.executed.append(query)


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason=(
        "BUG: LiveXPStore proxies expose async get()/append(), but XPGatekeeper "
        "calls them synchronously, so settle_segment_xp() receives a coroutine and "
        "raises AttributeError. /api/m4_5/grant_xp (called by the M3.3 approve "
        "flow) therefore never settles XP."
    ),
)
def test_live_store_settles_approved_segment():
    """AC-2 via LiveXPStore: an approved segment settles XP."""
    from services.m6_5_acid_gatekeeper.gatekeeper import XPGatekeeper
    from services.main import LiveXPStore

    gk = XPGatekeeper(LiveXPStore(FakeAsyncDB()))
    result = gk.settle_segment_xp(uuid.uuid4(), uuid.uuid4(), 20)
    assert result.success is True
