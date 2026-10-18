"""
D1(a) / DEVIATION-09 -- PII must be masked before any persona / tool-AI prompt reaches Gemini

[R07: POST §4.3] raw L1 text must not go to the cloud as-is
[R07: §5 Eguard] discrete text masking before upload
Risk: RISK-06 (role_id propagated through the mask)

The cloud client is always mocked; nothing here calls a real API.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

EMAIL = "boyu.chen@example.com"
TW_ID = "A123456789"
CARD = "4111 1111 1111 1111"


class _FakeClient:
    def __init__(self, sink: list[str]):
        self._sink = sink

    async def complete(self, prompt: str, **kwargs) -> str:
        self._sink.append(prompt)
        return "好"


@pytest.fixture
def captured_prompts(monkeypatch):
    import m4_1_router.routing_engine as routing_engine

    prompts: list[str] = []
    monkeypatch.setattr(routing_engine, "get_cloud_llm_client", lambda model: _FakeClient(prompts))
    return prompts


@pytest.fixture
def captured_logs(monkeypatch):
    import m0_4_logging.writer as writer

    events: list[dict] = []

    class _FakeWriter:
        async def emit(self, **kwargs):
            events.append(kwargs)

    monkeypatch.setattr(writer, "get_logger", lambda *a, **k: _FakeWriter())
    return events


def _assert_no_raw_pii(text: str) -> None:
    assert EMAIL not in text
    assert TW_ID not in text
    assert CARD not in text


class TestPersonaGeminiPrompt:
    async def test_user_message_masked(self, captured_prompts, captured_logs):
        from m4_2_persona.graph import _call_gemini

        await _call_gemini(
            "你是學長", f"我的信箱是 {EMAIL} ,身分證 {TW_ID}", "empathetic", None, role_id="role_csie"
        )
        assert len(captured_prompts) == 1
        _assert_no_raw_pii(captured_prompts[0])
        assert "[REDACTED_EMAIL]" in captured_prompts[0]
        assert "[REDACTED_ID]" in captured_prompts[0]

    async def test_history_masked(self, captured_prompts, captured_logs):
        from m4_2_persona.graph import _call_gemini

        history = [
            {"role": "user", "content": f"卡號是 {CARD}"},
            {"role": "assistant", "content": f"收到,寄到 {EMAIL} 嗎?"},
        ]
        await _call_gemini("你是學長", "對", "empathetic", history, role_id="role_csie")
        _assert_no_raw_pii(captured_prompts[0])
        assert "[REDACTED_CARD]" in captured_prompts[0]

    async def test_local_history_not_mutated(self, captured_prompts, captured_logs):
        """L1 copy stays intact locally; only the cloud-bound prompt is masked."""
        from m4_2_persona.graph import _call_gemini

        history = [{"role": "user", "content": f"寄到 {EMAIL}"}]
        await _call_gemini("你是學長", "好", "empathetic", history, role_id="role_csie")
        assert history[0]["content"] == f"寄到 {EMAIL}"

    async def test_mask_failure_blocks_cloud_call(self, monkeypatch, captured_prompts, captured_logs):
        """Fail closed: if masking breaks, the raw text must not be sent."""
        import m2_3_eguard.cloud_gate as cloud_gate
        from m4_2_persona.graph import _call_gemini

        def _boom(*a, **k):
            raise RuntimeError("eguard down")

        monkeypatch.setattr(cloud_gate, "mask_text_for_cloud", _boom)
        result = await _call_gemini("你是學長", f"寄到 {EMAIL}", "empathetic", None, role_id="r")
        assert result is None
        assert captured_prompts == []


class TestEpisodicMemoriesForCloud:
    def test_memories_masked(self):
        from m4_2_persona.graph import _sanitize_memories_for_cloud

        memories = [{"content": f"使用者說：我的信箱 {EMAIL}"}, {"content": "使用者說：今天好累"}]
        masked, entities = _sanitize_memories_for_cloud(memories, role_id="role_csie")
        assert EMAIL not in masked[0]["content"]
        assert masked[1]["content"] == "使用者說：今天好累"
        assert "EMAIL" in entities
        assert memories[0]["content"] == f"使用者說：我的信箱 {EMAIL}"


class TestToolAIGeminiPrompt:
    async def test_user_message_and_history_masked(self, captured_prompts, captured_logs):
        from m4_1_router.graph import _tool_ai_reply_gemini

        history = [{"role": "user", "content": f"之前說過 {CARD}"}]
        await _tool_ai_reply_gemini(f"幫我寫信給 {EMAIL}", [], history, role_id="role_csie")
        assert len(captured_prompts) == 1
        _assert_no_raw_pii(captured_prompts[0])
        assert "[REDACTED_EMAIL]" in captured_prompts[0]
        assert "[REDACTED_CARD]" in captured_prompts[0]


class TestMaskObservability:
    @pytest.mark.integration_risk("RISK-06")
    async def test_mask_event_logged_without_raw_pii(self, captured_prompts, captured_logs):
        from m4_2_persona.graph import _call_gemini

        await _call_gemini("你是學長", f"寄到 {EMAIL}", "empathetic", None, role_id="role_csie")
        mask_events = [e for e in captured_logs if e.get("action") == "pii_masked_before_cloud"]
        assert len(mask_events) == 1
        event = mask_events[0]
        assert event["module"] == "M2.3"
        assert event["role_id"] == "role_csie"
        assert EMAIL not in str(event)
        assert "EMAIL" in event["payload"]

    async def test_no_log_when_nothing_masked(self, captured_prompts, captured_logs):
        from m4_2_persona.graph import _call_gemini

        await _call_gemini("你是學長", "今天好累", "empathetic", None, role_id="role_csie")
        assert [e for e in captured_logs if e.get("action") == "pii_masked_before_cloud"] == []


class TestCJKAdjacentPII:
    def test_taiwan_id_adjacent_to_cjk_is_masked(self):
        """[D6] fixed: patterns use alphanumeric lookarounds instead of \\b."""
        from m2_3_eguard.cloud_gate import mask_text_for_cloud

        result = mask_text_for_cloud(f"身分證{TW_ID}", role_id="r")
        assert TW_ID not in result.sanitized_text
