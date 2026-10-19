"""
M0.5 Gemini quota guard -- test suite

SPEC: docs/modules/M0_5_synthetic_user_simulator_SPEC.md §7.4, §9.1 Q6, §9.2 Q8
Risk coverage: RISK-24 (synthetic ledger never touches data/coos.db)
"""
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m0_5_synthetic_sim.isolation import SYNTHETIC_APP_ID, RealDatabaseRefused  # noqa: E402
from m0_5_synthetic_sim.quota import (  # noqa: E402
    InMemoryLedger,
    ModelLimits,
    QuotaConfig,
    QuotaGuard,
    SqliteLedger,
    load_quota_config,
    pacific_day_start,
    plan_run,
)
from m0_5_synthetic_sim.quota.__main__ import main as quota_cli  # noqa: E402

MODEL = "gemini-3.1-flash-lite"
T0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)


def cfg(**kw) -> QuotaConfig:
    base = dict(
        mode="free_only",
        share_of_project_quota=1.0,
        models={MODEL: ModelLimits(rpm=10, tpm=1000, rpd=20)},
    )
    base.update(kw)
    return QuotaConfig(**base)


def guard(c: QuotaConfig | None = None) -> QuotaGuard:
    return QuotaGuard(c or cfg(), InMemoryLedger())


def body_429(quota_id: str, value: str | None = "20", retry: str | None = "35s",
             metric: str = "generativelanguage.googleapis.com/generate_content_free_tier_requests") -> dict:
    details = [{
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [{
            "quotaMetric": metric,
            "quotaId": quota_id,
            "quotaDimensions": {"location": "global", "model": MODEL},
            **({"quotaValue": value} if value is not None else {}),
        }],
    }]
    if retry:
        details.append({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry})
    return {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota", "details": details}}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_default_config_is_free_only_and_ascii():
    """§9.2 Q8:預設只用免費額度;設定檔純 ASCII (CLAUDE.md Windows 規則)"""
    c = load_quota_config()
    assert c.mode == "free_only"
    assert c.monthly_usd_cap == 0.0
    assert MODEL in c.models
    raw = (SERVICES / "m0_5_synthetic_sim" / "quota" / "quota_limits.toml").read_bytes()
    assert all(b < 128 for b in raw)


def test_default_limits_match_ai_studio_and_fallback_configured():
    """§9.1 Q11:預設值為使用者 AI Studio 專案頁面的實際數字 (2026-10-19)"""
    c = load_quota_config()
    assert all(m.verified for m in c.models.values())
    assert (c.models[MODEL].rpm, c.models[MODEL].tpm, c.models[MODEL].rpd) == (15, 250_000, 500)
    assert c.models["gemini-2.5-flash-lite"].rpd == 20
    assert c.fallback_model in c.models and c.models[c.fallback_model].rpd >= c.models[MODEL].rpd


def test_config_file_override(tmp_path):
    p = tmp_path / "q.toml"
    p.write_text('mode = "off"\nshare_of_project_quota = 1.0\n[models."m"]\nrpm = 1\ntpm = 1\nrpd = 1\n')
    c = load_quota_config(p)
    assert c.mode == "off" and c.models["m"].rpd == 1


def test_paid_capped_requires_cap_and_prices():
    with pytest.raises(ValueError):
        cfg(mode="paid_capped", monthly_usd_cap=0.0)
    with pytest.raises(ValueError):
        cfg(mode="paid_capped", monthly_usd_cap=5.0)          # prices still 0


# ---------------------------------------------------------------------------
# Basic gating
# ---------------------------------------------------------------------------

def test_mode_off_blocks_everything():
    d = guard(cfg(mode="off")).check(MODEL, 10, T0)
    assert not d.allowed and d.reason == "mode_off"


def test_unconfigured_model_refused():
    d = guard().check("gemini-9-ultra", 10, T0)
    assert not d.allowed and d.reason == "model_not_configured"


def test_rpm_limit_respects_share():
    g = guard(cfg(share_of_project_quota=0.5))                 # 10 RPM * 0.5 = 5
    for i in range(5):
        assert g.check(MODEL, 1, T0).allowed
        g.record_success(MODEL, 1, T0 + timedelta(seconds=i))
    d = g.check(MODEL, 1, T0 + timedelta(seconds=10))
    assert not d.allowed and d.reason == "rpm" and 0 < d.retry_after_s <= 60
    assert g.check(MODEL, 1, T0 + timedelta(seconds=61)).allowed


def test_tpm_limit():
    g = guard()
    g.record_success(MODEL, 900, T0)
    d = g.check(MODEL, 200, T0 + timedelta(seconds=5))
    assert not d.allowed and d.reason == "tpm"


def test_rpd_exhausted_until_pacific_midnight():
    g = guard()
    for i in range(20):
        g.record_success(MODEL, 1, T0 + timedelta(minutes=i))
    d = g.check(MODEL, 1, T0 + timedelta(hours=1))
    assert not d.allowed and d.reason == "rpd"
    next_day = pacific_day_start(T0) + timedelta(days=1, seconds=1)
    assert g.check(MODEL, 1, next_day).allowed


@pytest.mark.parametrize("now,expected_utc_hour", [
    (datetime(2026, 10, 19, 12, 0, tzinfo=UTC), 7),     # PDT (UTC-7)
    (datetime(2026, 12, 1, 12, 0, tzinfo=UTC), 8),      # PST (UTC-8)
    (datetime(2026, 11, 1, 9, 30, tzinfo=UTC), 7),      # 02:30 PDT on DST-end day; day began in PDT
    (datetime(2026, 3, 8, 12, 0, tzinfo=UTC), 8),       # DST-start day; midnight was still PST
])
def test_pacific_day_start(now, expected_utc_hour):
    """RPD 於太平洋時間午夜重置 (ai.google.dev rate-limits, 2026-10-15)"""
    start = pacific_day_start(now)
    assert start.tzinfo is not None and start <= now < start + timedelta(hours=25)
    assert start.astimezone(UTC).hour == expected_utc_hour


# ---------------------------------------------------------------------------
# Learning from 429
# ---------------------------------------------------------------------------

def test_429_per_day_learns_limit_and_blocks_until_reset():
    g = guard(cfg(models={MODEL: ModelLimits(rpm=10, tpm=1000, rpd=500)}))
    d = g.record_429(MODEL, body_429("GenerateRequestsPerDayPerProjectPerModel-FreeTier", value="250"), T0)
    assert not d.allowed and d.reason == "rpd"
    assert g.effective_limits(MODEL).rpd == 250
    assert not g.check(MODEL, 1, T0 + timedelta(hours=2)).allowed
    assert g.check(MODEL, 1, pacific_day_start(T0) + timedelta(days=1, seconds=1)).allowed


def test_429_per_minute_uses_retry_delay():
    g = guard()
    body = body_429("GenerateRequestsPerMinutePerProjectPerModel-FreeTier", value="8", retry="12s")
    d = g.record_429(MODEL, body, T0)
    assert d.reason == "rpm" and d.retry_after_s == pytest.approx(12)
    assert g.effective_limits(MODEL).rpm == 8
    assert not g.check(MODEL, 1, T0 + timedelta(seconds=5)).allowed
    assert g.check(MODEL, 1, T0 + timedelta(seconds=13)).allowed


def test_429_input_tokens_per_minute_learns_tpm():
    g = guard()
    metric = "generativelanguage.googleapis.com/generate_content_free_tier_input_token_count"
    quota_id = "GenerateContentInputTokensPerModelPerMinute-FreeTier"
    g.record_429(MODEL, body_429(quota_id, value="600", metric=metric), T0)
    assert g.effective_limits(MODEL).tpm == 600


def test_429_without_free_tier_latches_paid_detected():
    """free_only 模式下看到非 FreeTier 配額 → 專案已綁帳單 → 全面停用雲端呼叫,直到人工解除"""
    g = guard()
    body = body_429("GenerateRequestsPerDayPerProjectPerModel", metric="x/generate_content_requests")
    d = g.record_429(MODEL, body, T0)
    assert not d.allowed and d.reason == "paid_tier_detected"
    assert g.check(MODEL, 1, T0 + timedelta(days=3)).reason == "paid_tier_detected"
    g.clear_paid_latch()
    assert g.check(MODEL, 1, T0 + timedelta(days=3)).allowed


def test_unparseable_429_backs_off_60s():
    g = guard()
    d = g.record_429(MODEL, {"error": {"code": 429}}, T0)
    assert not d.allowed and d.retry_after_s == pytest.approx(60)


# ---------------------------------------------------------------------------
# Paid-capped mode (configurable, not default)
# ---------------------------------------------------------------------------

def test_paid_capped_monthly_cap_blocks():
    c = cfg(mode="paid_capped", monthly_usd_cap=1.0,
            models={MODEL: ModelLimits(rpm=1000, tpm=10**9, rpd=10**6, usd_per_1m_input=1.0, usd_per_1m_output=1.0)})
    g = guard(c)
    g.record_success(MODEL, 900_000, T0)                    # $0.90 spent this month
    assert g.check(MODEL, 50_000, T0 + timedelta(minutes=2)).allowed
    d = g.check(MODEL, 200_000, T0 + timedelta(minutes=2))
    assert not d.allowed and d.reason == "monthly_cap"


# ---------------------------------------------------------------------------
# SQLite ledger (persistence + RISK-24 isolation)
# ---------------------------------------------------------------------------

def test_sqlite_ledger_persists_usage_and_learned_limits(tmp_path):
    db = tmp_path / "coos_synthetic.db"
    g1 = QuotaGuard(cfg(models={MODEL: ModelLimits(rpm=10, tpm=1000, rpd=500)}), SqliteLedger(db))
    g1.record_success(MODEL, 5, T0)
    g1.record_429(MODEL, body_429("GenerateRequestsPerDayPerProjectPerModel-FreeTier", value="300"), T0)
    g2 = QuotaGuard(cfg(models={MODEL: ModelLimits(rpm=10, tpm=1000, rpd=500)}), SqliteLedger(db))
    assert g2.effective_limits(MODEL).rpd == 300
    assert g2.usage(MODEL, T0 + timedelta(minutes=1)).requests_today == 1
    assert not g2.check(MODEL, 1, T0 + timedelta(minutes=1)).allowed


@pytest.mark.integration_risk("RISK-24")
def test_sqlite_ledger_refuses_real_db(tmp_path):
    from config import Settings
    with pytest.raises(RealDatabaseRefused):
        SqliteLedger(Settings(_env_file=None).local_db_path)
    with pytest.raises(RealDatabaseRefused):
        SqliteLedger(tmp_path / "coos.db")


@pytest.mark.integration_risk("RISK-24")
def test_sqlite_ledger_rows_synthetic_and_sentinel(tmp_path):
    db = tmp_path / "coos_synthetic.db"
    QuotaGuard(cfg(), SqliteLedger(db)).record_success(MODEL, 1, T0)
    con = sqlite3.connect(db)
    assert con.execute("PRAGMA application_id").fetchone()[0] == SYNTHETIC_APP_ID
    assert con.execute("SELECT COUNT(*) FROM m0_5_quota_ledger WHERE is_synthetic IS NOT 1").fetchone()[0] == 0
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO m0_5_quota_ledger (model, kind, at_utc, is_synthetic) VALUES ('m','call','x',0)")


@pytest.mark.integration_risk("RISK-24")
def test_sqlite_ledger_refuses_foreign_db(tmp_path):
    db = tmp_path / "other.db"
    sqlite3.connect(db).execute("CREATE TABLE t (x)").connection.commit()
    with pytest.raises(RealDatabaseRefused):
        SqliteLedger(db)


# ---------------------------------------------------------------------------
# Planning + CLI
# ---------------------------------------------------------------------------

def test_plan_run_estimates_days():
    c = cfg(share_of_project_quota=0.5, models={MODEL: ModelLimits(rpm=15, tpm=250_000, rpd=500)})
    p = plan_run(c, MODEL, users=16, days=42, calls_per_user_day=1.3)
    assert p.total_calls == 874                               # ceil(16*42*1.3)
    assert p.effective_rpd == 250 and p.wall_days == 4


def test_cli_status_and_plan(tmp_path, capsys):
    db = tmp_path / "coos_synthetic.db"
    assert quota_cli(["--db", str(db), "status"]) == 0
    assert MODEL in capsys.readouterr().out
    assert quota_cli(["--db", str(db), "plan", "--users", "16", "--days", "42"]) == 0
    assert "wall_days" in capsys.readouterr().out
