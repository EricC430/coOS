"""
M4.6 -- Topic Anchor Dedup & Canonical ID

Two-phase deduplication for descriptive intent-anchored topic labels:
  Phase 1: Exact normalized text match
  Phase 2: Embedding cosine similarity >= SEMANTIC_MERGE_THRESHOLD (0.88)

Research: [R10 §Agent Workflow] topic identity convergence
Risks: RISK-06 (role_id scoped), RISK-12 (PII pre-filtered upstream)

Adapted from ai-elder-care DirectSevenPipeline dedup architecture,
redesigned for topic semantics (no temporal slot, no subject normalization).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

import numpy as np

SEMANTIC_MERGE_THRESHOLD = 0.88

TOPIC_ID_PREFIX = "topic_"
TOPIC_ID_HASH_LENGTH = 12

_PUNCTUATION_STRIP = re.compile(r"^[，。、！？；：,.!?;:~～\-—「」『』]+|[，。、！？；：,.!?;:~～\-—「」『』]+$")
_WHITESPACE = re.compile(r"\s+")


@dataclass
class TopicAnchor:
    id: str
    role_id: str
    label: str
    embedding: list[float] | None = None


def normalize_topic_text(text: str) -> str:
    """NFKC + compress whitespace + strip surrounding punctuation.

    Unlike event predicate normalization, does NOT strip trailing particles
    ('的', '了', etc.) because they carry semantic meaning in descriptive labels.
    e.g. '了解微積分極限的學習意義' -- '了' and '的' are semantic here.
    """
    text = unicodedata.normalize("NFKC", text.strip())
    text = _WHITESPACE.sub("", text)
    text = _PUNCTUATION_STRIP.sub("", text)
    return text


def generate_topic_id(role_id: str, normalized_label: str) -> str:
    """Deterministic topic ID: sha256(role_id + ':' + normalized_label)[:12].

    [RISK-06] role_id is part of the hash input, ensuring cross-role isolation.
    """
    sig = f"{role_id}:{normalized_label}".encode()
    digest = hashlib.sha256(sig).hexdigest()[:TOPIC_ID_HASH_LENGTH]
    return f"{TOPIC_ID_PREFIX}{digest}"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


async def resolve_topic(
    candidate_label: str,
    candidate_embedding: list[float] | None,
    existing_topics: list[TopicAnchor],
    role_id: str,
) -> tuple[str, bool]:
    """Two-phase topic resolution. Returns (topic_id, is_new).

    Phase 1: Exact normalized text match -> reuse existing topic
    Phase 2: Embedding cosine >= 0.88 -> merge into most similar existing topic
    Phase 3: Neither -> generate new deterministic topic_id
    """
    normalized = normalize_topic_text(candidate_label)

    # Phase 1: exact text match
    for topic in existing_topics:
        if normalize_topic_text(topic.label) == normalized:
            return topic.id, False

    # Phase 2: semantic similarity
    if candidate_embedding and existing_topics:
        best_sim = -1.0
        best_topic: TopicAnchor | None = None
        for topic in existing_topics:
            if topic.embedding:
                sim = _cosine_similarity(candidate_embedding, topic.embedding)
                if sim > best_sim:
                    best_sim = sim
                    best_topic = topic
        if best_sim >= SEMANTIC_MERGE_THRESHOLD and best_topic is not None:
            return best_topic.id, False

    # Phase 3: new topic
    new_id = generate_topic_id(role_id, normalized)
    return new_id, True
