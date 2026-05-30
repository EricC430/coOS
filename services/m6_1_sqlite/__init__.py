"""
M6.1 -- Local SQLite Schema definitions and connection init

SPEC: docs/modules/M6_1_sqlite_schemas_SPEC.md
Risk mitigation: RISK-05 (edge_event_buffer.source_log_id FK)
"""
from .init import init_sqlite, open_sqlite
from .models import (
    ChatTranscriptCreate,
    ChatTranscriptRead,
    EdgeEventBufferRead,
    RawTrackingLogCreate,
    RawTrackingLogRead,
    RoleImplicitStateCreate,
    RoleImplicitStateRead,
)

__all__ = [
    "init_sqlite",
    "open_sqlite",
    "ChatTranscriptRead",
    "ChatTranscriptCreate",
    "RawTrackingLogRead",
    "RawTrackingLogCreate",
    "EdgeEventBufferRead",
    "RoleImplicitStateRead",
    "RoleImplicitStateCreate",
]
