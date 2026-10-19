"""Gemini quota guard for the M0.5 realizer (SPEC §7.4, §9.2 Q8).

Every cloud call made by the simulator goes through:
    d = guard.check(model, est_tokens, now)      # before the call
    guard.record_success(model, tin, tout, now)  # after HTTP 200 (usageMetadata)
    guard.record_429(model, body, now)           # after HTTP 429
A denied check means: fall back to TemplateRealizer (or wait d.retry_after_s).

Limits = floor(min(configured, learned-from-429) * share_of_project_quota).
In free_only mode a 429 whose quota is not a FreeTier quota means the project has
billing attached; the guard latches and refuses all calls until a human clears it.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import BaseModel

from .clock import next_pacific_day_start, pacific_day_start, pacific_month_start
from .config import ModelLimits, QuotaConfig
from .ledger import QuotaLedger

DEFAULT_BACKOFF_S = 60.0


class Decision(BaseModel):
    allowed: bool
    # ok | mode_off | model_not_configured | paid_tier_detected | rpd | rpm | tpm | monthly_cap | rate_limited
    reason: str = "ok"
    retry_after_s: float = 0.0


class EffectiveLimits(BaseModel):
    rpm: int
    tpm: int
    rpd: int


class Usage(BaseModel):
    requests_last_minute: int
    tokens_last_minute: int
    requests_today: int
    month_usd: float


@dataclass(frozen=True)
class QuotaViolation:
    kind: str            # "rpd" | "rpm" | "tpm"
    quota_id: str
    value: int | None
    free_tier: bool


def _retry_delay_s(details: list[dict]) -> float | None:
    for d in details:
        if str(d.get("@type", "")).endswith("google.rpc.RetryInfo"):
            m = re.fullmatch(r"\s*([0-9.]+)s\s*", str(d.get("retryDelay", "")))
            if m:
                return float(m.group(1))
    return None


def parse_quota_failure(body: dict) -> tuple[list[QuotaViolation], float | None]:
    """Parse a Gemini 429 body (google.rpc.QuotaFailure + RetryInfo)."""
    details = (body or {}).get("error", {}).get("details", []) or []
    out: list[QuotaViolation] = []
    for d in details:
        if not str(d.get("@type", "")).endswith("google.rpc.QuotaFailure"):
            continue
        for v in d.get("violations", []) or []:
            qid = str(v.get("quotaId", ""))
            metric = str(v.get("quotaMetric", ""))
            if "PerDay" in qid:
                kind = "rpd"
            elif "token" in metric.lower() or "Tokens" in qid:
                kind = "tpm"
            elif "PerMinute" in qid:
                kind = "rpm"
            else:
                continue
            raw = v.get("quotaValue")
            value = int(raw) if raw is not None and str(raw).isdigit() else None
            free = "FreeTier" in qid or "free_tier" in metric
            out.append(QuotaViolation(kind, qid, value, free))
    return out, _retry_delay_s(details)


class QuotaGuard:
    def __init__(self, config: QuotaConfig, ledger: QuotaLedger) -> None:
        self.config = config
        self.ledger = ledger

    # -- limits ---------------------------------------------------------------
    def configured(self, model: str) -> ModelLimits | None:
        return self.config.models.get(model)

    def effective_limits(self, model: str) -> EffectiveLimits:
        lim = self.config.models[model]
        learned = self.ledger.learned(model)
        share = self.config.share_of_project_quota
        return EffectiveLimits(**{
            f: math.floor(min(getattr(lim, f), learned.get(f, getattr(lim, f))) * share)
            for f in ("rpm", "tpm", "rpd")
        })

    def _cost_usd(self, model: str, tokens_in: int, tokens_out: int) -> float:
        lim = self.config.models.get(model)
        if lim is None:
            return 0.0
        return (tokens_in * lim.usd_per_1m_input + tokens_out * lim.usd_per_1m_output) / 1_000_000

    def usage(self, model: str, now: datetime) -> Usage:
        minute = self.ledger.calls_since(model, now - timedelta(seconds=60))
        today = self.ledger.calls_since(model, pacific_day_start(now))
        month_start = pacific_month_start(now)
        month_usd = sum(
            self._cost_usd(m, c.tokens_in, c.tokens_out)
            for m in self.ledger.models_with_calls()
            for c in self.ledger.calls_since(m, month_start)
        )
        return Usage(
            requests_last_minute=len(minute),
            tokens_last_minute=sum(c.tokens_in + c.tokens_out for c in minute),
            requests_today=len(today),
            month_usd=month_usd,
        )

    # -- decisions ------------------------------------------------------------
    def check(self, model: str, est_tokens: int, now: datetime) -> Decision:
        if self.config.mode == "off":
            return Decision(allowed=False, reason="mode_off")
        if model not in self.config.models:
            return Decision(allowed=False, reason="model_not_configured")
        if self.config.mode == "free_only" and self.ledger.paid_latch():
            return Decision(allowed=False, reason="paid_tier_detected")

        block = self.ledger.active_block(model, now)
        if block is not None:
            return Decision(allowed=False, reason=block.reason, retry_after_s=(block.until - now).total_seconds())

        lim = self.effective_limits(model)
        if len(self.ledger.calls_since(model, pacific_day_start(now))) >= lim.rpd:
            return Decision(allowed=False, reason="rpd",
                            retry_after_s=(next_pacific_day_start(now) - now).total_seconds())

        window = self.ledger.calls_since(model, now - timedelta(seconds=60))
        if len(window) >= lim.rpm:
            oldest = min(c.at for c in window) if window else now
            return Decision(allowed=False, reason="rpm",
                            retry_after_s=max((oldest + timedelta(seconds=60) - now).total_seconds(), 0.001))
        used_tokens = sum(c.tokens_in + c.tokens_out for c in window)
        if used_tokens + est_tokens > lim.tpm:
            oldest = min((c.at for c in window), default=now)
            return Decision(allowed=False, reason="tpm",
                            retry_after_s=max((oldest + timedelta(seconds=60) - now).total_seconds(), 0.001))

        if self.config.mode == "paid_capped":
            lim_cfg = self.config.models[model]
            est_cost = est_tokens * max(lim_cfg.usd_per_1m_input, lim_cfg.usd_per_1m_output) / 1_000_000
            if self.usage(model, now).month_usd + est_cost > self.config.monthly_usd_cap:
                return Decision(allowed=False, reason="monthly_cap")
        return Decision(allowed=True)

    def record_success(self, model: str, tokens_in: int, now: datetime, tokens_out: int = 0) -> None:
        self.ledger.add_call(model, now, tokens_in, tokens_out)

    def record_429(self, model: str, body: dict, now: datetime) -> Decision:
        violations, retry = parse_quota_failure(body)
        if not violations:
            until = now + timedelta(seconds=retry or DEFAULT_BACKOFF_S)
            self.ledger.add_block(model, "rate_limited", until, now)
            return Decision(allowed=False, reason="rate_limited", retry_after_s=(until - now).total_seconds())

        if self.config.mode == "free_only" and not all(v.free_tier for v in violations):
            self.ledger.set_paid_latch(True, now)
            return Decision(allowed=False, reason="paid_tier_detected")

        worst: Decision | None = None
        for v in violations:
            if v.value is not None:
                self.ledger.set_learned(model, v.kind, v.value, now)
            until = next_pacific_day_start(now) if v.kind == "rpd" else now + timedelta(
                seconds=retry or DEFAULT_BACKOFF_S)
            self.ledger.add_block(model, v.kind, until, now)
            d = Decision(allowed=False, reason=v.kind, retry_after_s=(until - now).total_seconds())
            if worst is None or d.retry_after_s > worst.retry_after_s:
                worst = d
        return worst  # type: ignore[return-value]

    def clear_paid_latch(self, now: datetime | None = None) -> None:
        self.ledger.set_paid_latch(False, now or datetime.now().astimezone())


class PlanEstimate(BaseModel):
    model: str
    total_calls: int
    effective_rpd: int
    effective_rpm: int
    wall_days: int
    hours_per_day_at_rpm: float


def plan_run(config: QuotaConfig, model: str, users: int, days: int, calls_per_user_day: float = 1.3) -> PlanEstimate:
    """Estimate how many real days a Gemini-realizer run needs under the free tier."""
    lim = config.models[model]
    share = config.share_of_project_quota
    rpd = math.floor(lim.rpd * share)
    rpm = math.floor(lim.rpm * share)
    if rpd <= 0 or rpm <= 0:
        raise ValueError(f"effective limits for {model} are zero; check quota_limits.toml")
    total = math.ceil(round(users * days * calls_per_user_day, 6))
    per_day = min(total, rpd)
    return PlanEstimate(
        model=model,
        total_calls=total,
        effective_rpd=rpd,
        effective_rpm=rpm,
        wall_days=math.ceil(total / rpd),
        hours_per_day_at_rpm=round(per_day / rpm / 60, 2),
    )
