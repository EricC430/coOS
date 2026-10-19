import json
import logging
from unittest.mock import patch
from m4_11_zpd_pipeline.service import ZPDPipelineService
from m4_11_zpd_pipeline.telemetry import log_zpd_event


def test_telemetry_l1_privacy_audit(caplog):
    """
    [Principle I Privacy Audit]
    Verify that telemetry logs only record metadata and never raw chat transcripts.
    """
    with caplog.at_level(logging.INFO):
        log_zpd_event(
            event_type="challenge_drawn",
            user_id="audit_user",
            role_id="role_csie",
            challenge_id="zpd_test_audit",
            details={"task_type": "skill_stretch", "difficulty": "comfort"},
        )

    records = [r for r in caplog.records if "[R01][M4.11]" in r.message]
    assert len(records) >= 1
    log_line = records[0].message

    # Parse JSON from log line
    json_part = log_line.split("[R01][M4.11] ")[1]
    payload = json.loads(json_part)

    assert payload["module"] == "M4.11"
    assert payload["user_id"] == "audit_user"
    assert "transcript" not in payload
    assert "chat" not in payload
    assert "content" not in payload
