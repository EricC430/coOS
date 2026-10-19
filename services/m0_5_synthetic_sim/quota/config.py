"""Quota guard configuration (quota_limits.toml)."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

DEFAULT_CONFIG_PATH = Path(__file__).with_name("quota_limits.toml")


class ModelLimits(BaseModel):
    rpm: int = Field(ge=0)
    tpm: int = Field(ge=0)
    rpd: int = Field(ge=0)
    usd_per_1m_input: float = Field(default=0.0, ge=0)
    usd_per_1m_output: float = Field(default=0.0, ge=0)
    verified: bool = False
    checked_at: str = ""
    source: str = ""


class QuotaConfig(BaseModel):
    mode: Literal["off", "free_only", "paid_capped"] = "free_only"
    share_of_project_quota: float = Field(default=0.5, gt=0, le=1)
    monthly_usd_cap: float = Field(default=0.0, ge=0)
    default_model: str = "gemini-3.1-flash-lite"
    fallback_model: str | None = None
    models: dict[str, ModelLimits] = {}

    @model_validator(mode="after")
    def _paid_needs_cap_and_prices(self) -> QuotaConfig:
        if self.mode != "paid_capped":
            return self
        if self.monthly_usd_cap <= 0:
            raise ValueError("mode=paid_capped requires monthly_usd_cap > 0")
        unpriced = [m for m, lim in self.models.items() if lim.usd_per_1m_input <= 0 or lim.usd_per_1m_output <= 0]
        if unpriced:
            raise ValueError(f"mode=paid_capped requires prices for every model: {unpriced}")
        return self


def load_quota_config(path: Path | None = None) -> QuotaConfig:
    with open(path or DEFAULT_CONFIG_PATH, "rb") as f:
        return QuotaConfig.model_validate(tomllib.load(f))
