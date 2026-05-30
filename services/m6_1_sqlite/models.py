"""
M6.1 v1.1 -- Pydantic v2 models for local SQLite L1 tables

SPEC: docs/modules/M6_1_sqlite_schemas_SPEC.md v1.1
Privacy: ALL models here are L1 (local-only, never cloud-synced).
Research:
  [R03 §3] paralinguistic_metadata for tone state machine (M4.2 input)
  [R08 §五] audio_path -- optional attachment for reflection enrichment

Tables in scope:
  chat_transcripts      (L1 -- raw dialogue, never leaves device)
  raw_tracking_logs     (L1 -- OS activity, never leaves device)
  edge_event_buffer     (L2 -- pending intent vectors before cloud sync)
  role_implicit_states  (L2 -- Valence-Arousal Persona state, device-local)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Chat Transcripts  (L1 -- never cloud-synced)
# ---------------------------------------------------------------------------

class ChatTranscriptRead(BaseModel):
    id: str  # SQLite uses TEXT UUIDs
    user_id: str
    role_id: str
    expert_id: str | None = None
    session_id: str | None = None
    role: Literal["user", "assistant", "system"]
    content: str         # L1: raw text, never leaves device
    token_count: int | None = None
    created_at: str      # ISO-8601 string from SQLite

    # v1.1 extensions
    project: str | None = None       # project/course tag for GraphRAG filtering
    audio_path: str | None = None    # L1: local file path only, never cloud
    paralinguistic_metadata: str | None = None  # JSON: tempo/pitch/stress for M4.2

    model_config = {"from_attributes": True}


class ChatTranscriptCreate(BaseModel):
    user_id: str
    role_id: str
    expert_id: str | None = None
    session_id: str | None = None
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)
    token_count: int | None = Field(None, ge=0)

    # v1.1 extensions
    project: str | None = None
    audio_path: str | None = None          # local file path; never uploaded
    paralinguistic_metadata: str | None = None  # JSON string


# ---------------------------------------------------------------------------
# Raw Tracking Logs  (L1 -- OS activity log, never leaves device)
# ---------------------------------------------------------------------------

class RawTrackingLogRead(BaseModel):
    id: str
    user_id: str
    role_id: str
    event_type: str     # e.g. "app_focus", "keystroke_burst", "idle"
    payload: str        # JSON blob -- L1, device-local only
    recorded_at: str    # ISO-8601 string

    model_config = {"from_attributes": True}


class RawTrackingLogCreate(BaseModel):
    user_id: str
    role_id: str
    event_type: str = Field(..., min_length=1, max_length=50)
    payload: str = Field(..., min_length=2)  # at least "{}"


# ---------------------------------------------------------------------------
# Edge Event Buffer  (L2 -- intent vectors pending cloud sync)
# ---------------------------------------------------------------------------

class EdgeEventBufferRead(BaseModel):
    id: str
    user_id: str
    role_id: str
    source_log_id: str
    intent_vector: str  # base64/JSON -- compressed by Gemma edge model
    is_synced: bool = False
    synced_at: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Role Implicit States  (L2 -- Valence-Arousal, device-local per SPEC §9)
# ---------------------------------------------------------------------------

class RoleImplicitStateRead(BaseModel):
    """
    [R03 §6] Short-lived Persona affect state. LOCAL-ONLY.
    Never cloud-synced -- Valence/Arousal values are raw inference output.
    """
    id: str
    user_id: str
    role_id: str
    label: str          # e.g. "defensive", "engaged", "fatigued"
    confidence: float   # [0.0, 1.0]
    inferred_at: str
    expires_at: str | None = None
    source_module: str = "M4.8"

    # v1.1: Valence-Arousal circumplex model [R03 §6]
    valence: float | None = None   # -1.0 (sad) .. +1.0 (happy)
    arousal: float | None = None   # -1.0 (calm) .. +1.0 (excited)
    raw_triggers: str | None = None  # JSON array of telemetry event types

    model_config = {"from_attributes": True}


class RoleImplicitStateCreate(BaseModel):
    user_id: str
    role_id: str
    label: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    expires_at: str | None = None
    source_module: str = "M4.8"

    # v1.1: Valence-Arousal
    valence: float | None = Field(None, ge=-1.0, le=1.0)
    arousal: float | None = Field(None, ge=-1.0, le=1.0)
    raw_triggers: str | None = None
