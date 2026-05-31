"""M2.1 Event Debouncer & Queueing Engine

SPEC: docs/modules/M2_1_event_debouncing_SPEC.md v1.1
[R08: §三.1 警報疲勞] debounce reduces cognitive load from over-triggering
[R02: REMT §動態上下文工程] role switch forces flush to prevent batch contamination
"""
from .debouncer import EventDebouncer
from .schema import EventBatch, RawTelemetryEvent

__all__ = ["EventDebouncer", "EventBatch", "RawTelemetryEvent"]
