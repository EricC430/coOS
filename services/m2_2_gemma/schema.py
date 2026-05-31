"""M2.2 IntentVector -- de-identified semantic output from Gemma edge inference

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.2
[R07: 意圖向量 §4.4] adapted from soft-prompt tensor to JSON + sentence embedding
Privacy: L2 -- no raw plaintext, only de-identified labels and embeddings
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class IntentVector(BaseModel):
    """De-identified intent vector output from Gemma edge inference.

    Fields:
        source_log_id: FK to raw_tracking_logs.id for local counter-abductive validation (RISK-05)
        role_id: role context at inference time, used by M5.1 to create role-dimensional graph edges
        intent_label: de-identified abstract label (e.g. "calculus_homework_probing")
        context_summary: de-identified context summary, no concrete names
        semantic_embedding: 2048-dim sentence embedding of de-identified text
        frustration_level: estimated frustration 0.0..1.0
        valence: emotional valence -1.0(negative)..1.0(positive), aligned with M6.4 VA model
        arousal: emotional arousal 0.0(calm)..1.0(excited), aligned with M6.4 VA model
        stripped_entities_count: number of concrete entities/variables removed
        inference_mode: 'gemma_edge' | 'rule_based_fallback' -- must be set on degradation
    """

    id: str = Field(default_factory=_uuid)
    created_at: datetime = Field(default_factory=_utcnow)

    # RISK-05 mitigation: both fields are mandatory, even in fallback mode
    source_log_id: str = Field(..., description="FK to raw_tracking_logs.id (RISK-05)")
    role_id: str = Field(..., description="Role context at inference time, for M5.1 graph edges")

    intent_label: str = Field(..., description="De-identified abstract intent label")
    context_summary: str = Field(..., description="De-identified context summary")
    semantic_embedding: list[float] = Field(
        default_factory=list,
        description="2048-dim sentence embedding of de-identified text",
    )

    frustration_level: float = Field(default=0.0, ge=0.0, le=1.0)
    valence: float = Field(default=0.0, ge=-1.0, le=1.0)
    arousal: float = Field(default=0.0, ge=0.0, le=1.0)
    stripped_entities_count: int = Field(default=0)
    inference_mode: Literal["gemma_edge", "rule_based_fallback"] = "gemma_edge"
