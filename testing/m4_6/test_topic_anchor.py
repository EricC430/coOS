"""
M4.6 -- Topic Anchor System Tests

Tests for the upgraded topic detection: descriptive intent-anchored labels,
two-phase dedup (exact text + embedding cosine), canonical ID generation,
and batch confirmation path.

Research: [R10 §Agent Workflow] [R02 §Dynamic State Decode]
Risks: RISK-06 (role isolation), RISK-08 (BDI separation), RISK-12 (PII filtering)
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

# ---------------------------------------------------------------------------
# Test: Topic Dedup Module
# ---------------------------------------------------------------------------


class TestNormalizeTopicText:
    """normalize_topic_text: NFKC + compress whitespace + strip punctuation.
    Must NOT strip semantic particles (unlike event predicate normalization)."""

    def test_nfkc_normalization(self):
        from m4_6_observer.topic_dedup import normalize_topic_text
        # Full-width to half-width
        assert normalize_topic_text("ＡＢＣ") == "ABC"

    def test_strips_surrounding_punctuation(self):
        from m4_6_observer.topic_dedup import normalize_topic_text
        assert normalize_topic_text("，了解微積分極限。") == "了解微積分極限"

    def test_preserves_semantic_particles(self):
        """Critical: '了解' must not have '了' stripped -- it's semantic, not a trailing particle."""
        from m4_6_observer.topic_dedup import normalize_topic_text
        result = normalize_topic_text("了解微積分極限的學習意義")
        assert result == "了解微積分極限的學習意義"

    def test_compresses_whitespace(self):
        from m4_6_observer.topic_dedup import normalize_topic_text
        assert normalize_topic_text("探索  個人  職涯方向") == "探索個人職涯方向"


class TestGenerateTopicId:
    """Deterministic topic ID: sha256(role_id + ':' + normalized_label)[:12]"""

    def test_deterministic_same_input(self):
        from m4_6_observer.topic_dedup import generate_topic_id
        id1 = generate_topic_id("role_csie", "了解微積分極限的學習意義")
        id2 = generate_topic_id("role_csie", "了解微積分極限的學習意義")
        assert id1 == id2

    def test_different_role_different_id(self):
        """[RISK-06] Different roles must produce different topic IDs."""
        from m4_6_observer.topic_dedup import generate_topic_id
        id1 = generate_topic_id("role_csie", "了解微積分極限的學習意義")
        id2 = generate_topic_id("role_family", "了解微積分極限的學習意義")
        assert id1 != id2

    def test_id_format(self):
        from m4_6_observer.topic_dedup import generate_topic_id
        tid = generate_topic_id("role_csie", "探索職涯方向")
        assert tid.startswith("topic_")
        assert len(tid) == len("topic_") + 12


class TestResolveTopic:
    """Two-phase dedup: exact text match -> embedding cosine >= 0.88"""

    @pytest.fixture
    def existing_topics(self):
        from m4_6_observer.topic_dedup import TopicAnchor
        import numpy as np
        # Create two orthogonal-ish embeddings for proper cosine separation
        rng = np.random.default_rng(42)
        emb_a = rng.standard_normal(384).tolist()
        emb_b = rng.standard_normal(384).tolist()
        return [
            TopicAnchor(
                id="topic_aaa111bbb222",
                role_id="role_csie",
                label="了解微積分極限的學習意義",
                embedding=emb_a,
            ),
            TopicAnchor(
                id="topic_ccc333ddd444",
                role_id="role_csie",
                label="廣泛探索個人職涯方向",
                embedding=emb_b,
            ),
        ]

    @pytest.mark.asyncio
    async def test_exact_text_match(self, existing_topics):
        from m4_6_observer.topic_dedup import resolve_topic
        topic_id, is_new = await resolve_topic(
            candidate_label="了解微積分極限的學習意義",
            candidate_embedding=[0.1] * 384,
            existing_topics=existing_topics,
            role_id="role_csie",
        )
        assert topic_id == "topic_aaa111bbb222"
        assert is_new is False

    @pytest.mark.asyncio
    async def test_semantic_match_above_threshold(self, existing_topics):
        """Cosine >= 0.88 should match to existing topic."""
        import numpy as np
        from m4_6_observer.topic_dedup import resolve_topic
        # Add small noise to first topic's embedding -> cosine ~ 0.99
        base = np.array(existing_topics[0].embedding)
        noise = np.random.default_rng(99).standard_normal(384) * 0.01
        similar_embedding = (base + noise).tolist()
        topic_id, is_new = await resolve_topic(
            candidate_label="理解微積分極限的意義",  # text different but semantically same
            candidate_embedding=similar_embedding,
            existing_topics=existing_topics,
            role_id="role_csie",
        )
        assert is_new is False
        assert topic_id == "topic_aaa111bbb222"

    @pytest.mark.asyncio
    async def test_new_topic_below_threshold(self, existing_topics):
        """Cosine < 0.88 should create new topic."""
        import numpy as np
        from m4_6_observer.topic_dedup import resolve_topic
        # Generate a random vector that is very unlikely to be close to either existing
        rng = np.random.default_rng(123)
        different_embedding = rng.standard_normal(384).tolist()
        topic_id, is_new = await resolve_topic(
            candidate_label="學習如何寫履歷",
            candidate_embedding=different_embedding,
            existing_topics=existing_topics,
            role_id="role_csie",
        )
        assert is_new is True
        assert topic_id.startswith("topic_")

    @pytest.mark.asyncio
    async def test_no_existing_topics_creates_new(self):
        import numpy as np
        from m4_6_observer.topic_dedup import resolve_topic
        rng = np.random.default_rng(7)
        topic_id, is_new = await resolve_topic(
            candidate_label="了解微積分極限的學習意義",
            candidate_embedding=rng.standard_normal(384).tolist(),
            existing_topics=[],
            role_id="role_csie",
        )
        assert is_new is True


# ---------------------------------------------------------------------------
# Test: Topic Detector (new prompt-based detection)
# ---------------------------------------------------------------------------


class TestTopicDetectorPrompt:
    """The new topic detector should extract intent-anchored descriptive labels."""

    @pytest.mark.asyncio
    async def test_new_topic_extraction(self):
        """LLM returns a new descriptive topic with intent and motivation."""
        from m4_6_observer.topic_detector import detect_topic_anchor

        mock_gemma = AsyncMock()
        mock_gemma.generate_text.return_value = (
            '{"new": "了解微積分極限的學習意義", '
            '"intent": "搞懂為什麼要學極限", '
            '"motivation": "期中考前建立概念框架"}'
        )
        mock_db = AsyncMock()
        mock_db.fetch_all.return_value = []
        mock_eguard = MagicMock()
        mock_eguard.mask_pii.side_effect = lambda text: MagicMock(sanitized_text=text)
        mock_sse = AsyncMock()

        result = await detect_topic_anchor(
            user_msg="我想搞懂微積分極限到底為什麼重要，不是只想會算題目",
            role_id="role_csie",
            db=mock_db,
            eguard=mock_eguard,
            sse=mock_sse,
            gemma=mock_gemma,
        )

        assert result is not None
        assert result.label == "了解微積分極限的學習意義"
        assert result.intent == "搞懂為什麼要學極限"
        assert result.motivation == "期中考前建立概念框架"
        assert result.is_new is True

    @pytest.mark.asyncio
    async def test_match_existing_topic(self):
        """LLM matches to an existing topic label."""
        from m4_6_observer.topic_detector import detect_topic_anchor

        mock_gemma = AsyncMock()
        mock_gemma.generate_text.return_value = '{"match": "了解微積分極限的學習意義"}'
        mock_db = AsyncMock()
        mock_db.fetch_all.return_value = [
            {"id": "topic_abc", "label": "了解微積分極限的學習意義",
             "embedding": None, "role_id": "role_csie"}
        ]
        mock_eguard = MagicMock()
        mock_eguard.mask_pii.return_value = MagicMock(
            sanitized_text="了解微積分極限的學習意義"
        )
        mock_sse = AsyncMock()

        result = await detect_topic_anchor(
            user_msg="繼續聊微積分極限那個主題",
            role_id="role_csie",
            db=mock_db,
            eguard=mock_eguard,
            sse=mock_sse,
            gemma=mock_gemma,
        )

        assert result is not None
        assert result.is_new is False
        assert result.topic_id == "topic_abc"

    @pytest.mark.asyncio
    async def test_no_topic_for_greeting(self):
        """Greetings/small talk should return None."""
        from m4_6_observer.topic_detector import detect_topic_anchor

        mock_gemma = AsyncMock()
        mock_gemma.generate_text.return_value = '{"none": true}'
        mock_db = AsyncMock()
        mock_db.fetch_all.return_value = []
        mock_eguard = MagicMock()
        mock_sse = AsyncMock()

        result = await detect_topic_anchor(
            user_msg="嗨你好",
            role_id="role_csie",
            db=mock_db,
            eguard=mock_eguard,
            sse=mock_sse,
            gemma=mock_gemma,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_pii_filtered_label(self):
        """[RISK-12] PII in label must be filtered before storage."""
        from m4_6_observer.topic_detector import detect_topic_anchor

        mock_gemma = AsyncMock()
        mock_gemma.generate_text.return_value = (
            '{"new": "幫陳小明完成OpenStack部署", '
            '"intent": "完成部署", "motivation": "課程需要"}'
        )
        mock_db = AsyncMock()
        mock_db.fetch_all.return_value = []
        mock_eguard = MagicMock()
        mock_eguard.mask_pii.return_value = MagicMock(
            sanitized_text="[REDACTED]完成OpenStack部署"
        )
        mock_sse = AsyncMock()

        result = await detect_topic_anchor(
            user_msg="幫陳小明完成OpenStack部署",
            role_id="role_csie",
            db=mock_db,
            eguard=mock_eguard,
            sse=mock_sse,
            gemma=mock_gemma,
        )
        # Should be rejected because label contains [REDACTED]
        assert result is None


# ---------------------------------------------------------------------------
# Test: Batch Confirmation Path (session close)
# ---------------------------------------------------------------------------


class TestBatchConfirmation:
    """Session-end batch path: confirm/correct label + extract context."""

    @pytest.mark.asyncio
    async def test_confirm_and_extract_context(self):
        from m4_6_observer.topic_batch_confirm import batch_confirm_topic

        mock_gemma = AsyncMock()
        mock_gemma.generate_text.return_value = (
            '{"label_confirmed": true, '
            '"corrected_label": null, '
            '"context_summary": "使用者理解了epsilon-delta定義的直覺意義", '
            '"intent_update": null, '
            '"motivation_update": null, '
            '"progress_note": "已完成極限定義的概念理解"}'
        )
        mock_db = AsyncMock()
        mock_db.fetch_thread_transcripts.return_value = [
            {"role": "user", "content": "極限的epsilon-delta定義到底在幹嘛"},
            {"role": "assistant", "content": "epsilon-delta定義的核心概念是..."},
        ]

        result = await batch_confirm_topic(
            thread_id="thread_001",
            topic_id="topic_abc",
            realtime_label="了解微積分極限的學習意義",
            role_id="role_csie",
            gemma=mock_gemma,
            db=mock_db,
        )

        assert result is not None
        assert result.label_confirmed is True
        assert result.context_summary == "使用者理解了epsilon-delta定義的直覺意義"
        assert result.progress_note == "已完成極限定義的概念理解"

    @pytest.mark.asyncio
    async def test_correct_label(self):
        """Batch path may correct a poorly detected realtime label."""
        from m4_6_observer.topic_batch_confirm import batch_confirm_topic

        mock_gemma = AsyncMock()
        mock_gemma.generate_text.return_value = (
            '{"label_confirmed": false, '
            '"corrected_label": "釐清微積分極限epsilon-delta定義的直覺", '
            '"context_summary": "討論集中在定義的直覺理解", '
            '"intent_update": "理解epsilon-delta的幾何意義", '
            '"motivation_update": null, '
            '"progress_note": null}'
        )
        mock_db = AsyncMock()
        mock_db.fetch_thread_transcripts.return_value = [
            {"role": "user", "content": "epsilon-delta到底在說什麼"},
        ]

        result = await batch_confirm_topic(
            thread_id="thread_002",
            topic_id="topic_abc",
            realtime_label="了解微積分極限的學習意義",
            role_id="role_csie",
            gemma=mock_gemma,
            db=mock_db,
        )

        assert result.label_confirmed is False
        assert result.corrected_label == "釐清微積分極限epsilon-delta定義的直覺"
        assert result.intent_update == "理解epsilon-delta的幾何意義"

    @pytest.mark.asyncio
    async def test_empty_transcript_returns_none(self):
        """No transcript -> skip batch confirmation."""
        from m4_6_observer.topic_batch_confirm import batch_confirm_topic

        mock_gemma = AsyncMock()
        mock_db = AsyncMock()
        mock_db.fetch_thread_transcripts.return_value = []

        result = await batch_confirm_topic(
            thread_id="thread_003",
            topic_id="topic_abc",
            realtime_label="test",
            role_id="role_csie",
            gemma=mock_gemma,
            db=mock_db,
        )

        assert result is None


# ---------------------------------------------------------------------------
# Test: Integration Risk Guards
# ---------------------------------------------------------------------------


class TestRiskGuards:
    """[RISK-06, RISK-12] Privacy and role isolation invariants."""

    def test_topic_id_scoped_by_role(self):
        """[RISK-06] Same label in different roles must NOT collide."""
        from m4_6_observer.topic_dedup import generate_topic_id
        id_csie = generate_topic_id("role_csie", "探索職涯方向")
        id_family = generate_topic_id("role_family", "探索職涯方向")
        assert id_csie != id_family

    @pytest.mark.asyncio
    async def test_eguard_applied_to_all_fields(self):
        """[RISK-12] intent and motivation must also be PII-filtered."""
        from m4_6_observer.topic_detector import detect_topic_anchor

        mock_gemma = AsyncMock()
        mock_gemma.generate_text.return_value = (
            '{"new": "協助完成專案", '
            '"intent": "幫陳教授完成實驗", '
            '"motivation": "拿推薦信"}'
        )
        mock_db = AsyncMock()
        mock_db.fetch_all.return_value = []
        mock_eguard = MagicMock()
        # Eguard strips PII from all fields
        mock_eguard.mask_pii.side_effect = lambda text: MagicMock(
            sanitized_text=text.replace("陳教授", "[REDACTED]")
        )
        mock_sse = AsyncMock()

        result = await detect_topic_anchor(
            user_msg="幫陳教授完成實驗報告",
            role_id="role_csie",
            db=mock_db,
            eguard=mock_eguard,
            sse=mock_sse,
            gemma=mock_gemma,
        )

        if result:
            assert "陳教授" not in (result.intent or "")
