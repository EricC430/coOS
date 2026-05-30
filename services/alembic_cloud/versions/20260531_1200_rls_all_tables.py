"""RLS (Row Level Security) policies for all cloud tables

Revision ID: cloud_20260531_1200
Revises: cloud_20260531_1100
Create Date: 2026-05-31 12:00:00.000000

Enables RLS on every L3 cloud table and defines per-user isolation policies.
Supabase uses auth.uid() from the JWT to identify the current user.

Architecture:
  - users        : user can only read/write their own row
  - roles        : isolated by roles.user_id
  - ai_experts   : isolated via roles.user_id join
  - xp_ledger    : isolated by xp_ledger.user_id
  - user_badges  : isolated by user_badges.user_id
  - badge_definitions : public read (admin-managed catalog)
  - role_projects, role_settings : isolated via roles.user_id
  - daily_reflections, daily_reflection_segments : isolated by user_id or join

Privacy: [CLAUDE.md §隱私三層原則] L3 data only. L1/L2 never reach this DB.
RISK-12: xp_ledger.reason never contains raw user text (enforced upstream).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "cloud_20260531_1200"
down_revision: str | None = "cloud_20260531_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---------- users ----------
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY users_self_only ON users
        FOR ALL TO authenticated
        USING (id = auth.uid())
        WITH CHECK (id = auth.uid())
    """)

    # ---------- roles ----------
    op.execute("ALTER TABLE roles ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY roles_owner ON roles
        FOR ALL TO authenticated
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
    """)

    # ---------- ai_experts ----------
    # Access via roles.user_id: user owns the role that owns the expert
    op.execute("ALTER TABLE ai_experts ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY ai_experts_owner ON ai_experts
        FOR ALL TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM roles
                WHERE roles.id = ai_experts.role_id
                  AND roles.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM roles
                WHERE roles.id = ai_experts.role_id
                  AND roles.user_id = auth.uid()
            )
        )
    """)

    # ---------- xp_ledger ----------
    op.execute("ALTER TABLE xp_ledger ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY xp_ledger_owner ON xp_ledger
        FOR ALL TO authenticated
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
    """)

    # ---------- badge_definitions (public catalog, read-only for users) ----------
    op.execute("ALTER TABLE badge_definitions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY badge_definitions_public_read ON badge_definitions
        FOR SELECT TO authenticated
        USING (true)
    """)

    # ---------- user_badges ----------
    op.execute("ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_badges_owner ON user_badges
        FOR ALL TO authenticated
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
    """)

    # ---------- role_projects ----------
    op.execute("ALTER TABLE role_projects ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY role_projects_owner ON role_projects
        FOR ALL TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM roles
                WHERE roles.id = role_projects.role_id
                  AND roles.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM roles
                WHERE roles.id = role_projects.role_id
                  AND roles.user_id = auth.uid()
            )
        )
    """)

    # ---------- role_settings ----------
    op.execute("ALTER TABLE role_settings ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY role_settings_owner ON role_settings
        FOR ALL TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM roles
                WHERE roles.id = role_settings.role_id
                  AND roles.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM roles
                WHERE roles.id = role_settings.role_id
                  AND roles.user_id = auth.uid()
            )
        )
    """)

    # ---------- daily_reflections ----------
    op.execute("ALTER TABLE daily_reflections ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY daily_reflections_owner ON daily_reflections
        FOR ALL TO authenticated
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
    """)

    # ---------- daily_reflection_segments ----------
    # Access via daily_reflections.user_id
    op.execute("ALTER TABLE daily_reflection_segments ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY daily_reflection_segments_owner ON daily_reflection_segments
        FOR ALL TO authenticated
        USING (
            EXISTS (
                SELECT 1 FROM daily_reflections
                WHERE daily_reflections.id = daily_reflection_segments.reflection_id
                  AND daily_reflections.user_id = auth.uid()
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM daily_reflections
                WHERE daily_reflections.id = daily_reflection_segments.reflection_id
                  AND daily_reflections.user_id = auth.uid()
            )
        )
    """)


def downgrade() -> None:
    tables_simple = [
        "users", "roles", "xp_ledger", "badge_definitions",
        "user_badges", "daily_reflections",
    ]
    tables_joined = [
        "ai_experts", "role_projects", "role_settings", "daily_reflection_segments",
    ]
    policy_map = {
        "users": "users_self_only",
        "roles": "roles_owner",
        "ai_experts": "ai_experts_owner",
        "xp_ledger": "xp_ledger_owner",
        "badge_definitions": "badge_definitions_public_read",
        "user_badges": "user_badges_owner",
        "role_projects": "role_projects_owner",
        "role_settings": "role_settings_owner",
        "daily_reflections": "daily_reflections_owner",
        "daily_reflection_segments": "daily_reflection_segments_owner",
    }
    for table in tables_simple + tables_joined:
        policy = policy_map[table]
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
