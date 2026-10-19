"""M0.5 Gemini quota CLI.

Run from services/:
    uv run python -m m0_5_synthetic_sim.quota status
    uv run python -m m0_5_synthetic_sim.quota plan --users 16 --days 42
    uv run python -m m0_5_synthetic_sim.quota clear-paid-latch     # only after confirming no billing
Options: --config <toml> (default quota_limits.toml), --db <path> (default data/coos_synthetic.db)
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from .clock import next_pacific_day_start
from .config import DEFAULT_CONFIG_PATH, load_quota_config
from .guard import QuotaGuard, plan_run
from .ledger import SqliteLedger

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "data" / "coos_synthetic.db"
AI_STUDIO_LIMITS_URL = "https://aistudio.google.com/usage?tab=rate-limit"


def _status(guard: QuotaGuard, now: datetime) -> None:
    c = guard.config
    print(f"mode={c.mode} share_of_project_quota={c.share_of_project_quota} monthly_usd_cap={c.monthly_usd_cap}")
    print(f"paid_latch={guard.ledger.paid_latch()} next_rpd_reset_utc={next_pacific_day_start(now).isoformat()}")
    for model, lim in c.models.items():
        eff = guard.effective_limits(model)
        use = guard.usage(model, now)
        learned = guard.ledger.learned(model)
        block = guard.ledger.active_block(model, now)
        print(f"\n[{model}] verified={lim.verified} checked_at={lim.checked_at}")
        print(f"  configured rpm={lim.rpm} tpm={lim.tpm} rpd={lim.rpd}")
        print(f"  learned    {learned or '-'}")
        print(f"  effective  rpm={eff.rpm} tpm={eff.tpm} rpd={eff.rpd}")
        print(f"  used       last_minute={use.requests_last_minute} req / {use.tokens_last_minute} tok, "
              f"today={use.requests_today}/{eff.rpd}, month_usd={use.month_usd:.4f}")
        print(f"  block      {f'{block.reason} until {block.until.isoformat()}' if block else '-'}")
    print(f"\nverify limits for your project at {AI_STUDIO_LIMITS_URL}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    p = argparse.ArgumentParser(prog="m0_5_synthetic_sim.quota")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    pl = sub.add_parser("plan")
    pl.add_argument("--users", type=int, default=16)
    pl.add_argument("--days", type=int, default=42)
    pl.add_argument("--calls-per-user-day", type=float, default=1.3)
    pl.add_argument("--model", default=None)
    sub.add_parser("clear-paid-latch")
    args = p.parse_args(argv)

    config = load_quota_config(args.config)
    now = datetime.now(UTC)
    if args.cmd == "plan":
        est = plan_run(config, args.model or config.default_model, args.users, args.days, args.calls_per_user_day)
        for k, v in est.model_dump().items():
            print(f"{k}={v}")
        return 0

    guard = QuotaGuard(config, SqliteLedger(args.db))
    if args.cmd == "status":
        _status(guard, now)
    elif args.cmd == "clear-paid-latch":
        guard.clear_paid_latch(now)
        print("paid_latch cleared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
