"""
M4.2.2 -- Persona Episodic Memory Store

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R11: Park et al. ss3.2] Retrieval scoring = recency x importance x relevance
          [R15: MemGPT ss Memory Management] Tiered memory, token budget <= 350
          [R19: sqlite-vec] Local vector search
Risk: RISK-06 (role_id, persona_id double-key isolation)
      RISK-12 (PII masking before write)
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# [R11] Retrieval scoring weights
ALPHA_RECENCY = 0.3
BETA_IMPORTANCE = 0.4
GAMMA_RELEVANCE = 0.3
RECENCY_DECAY = 0.995  # per hour


@dataclass
class Memory:
    """Single episodic memory entry."""
    id: str
    role_id: str
    persona_id: str
    kind: str  # "observation" | "reflection" | "commitment"
    content: str
    importance: float  # 0.0 - 1.0
    created_at: float  # unix timestamp
    last_accessed: float  # unix timestamp
    embedding: list[float] | None = None


class PersonaMemoryStore:
    """
    [R11][R15][R19] (role_id, persona_id) double-key isolated episodic memory.

    All memories stay in local SQLite (L1 privacy tier).
    PII must be masked before calling write_* methods.
    """

    def __init__(self):
        self._memories: dict[str, Memory] = {}

    def write_observation(
        self,
        role_id: str,
        persona_id: str,
        content: str,
        importance: float = 0.5,
        embedding: list[float] | None = None,
    ) -> str:
        """[R11 ss3.1] Write an observation memory."""
        return self._write(role_id, persona_id, "observation", content, importance, embedding)

    def write_reflection(
        self,
        role_id: str,
        persona_id: str,
        content: str,
        importance: float = 0.7,
        embedding: list[float] | None = None,
    ) -> str:
        """[R11 ss3.3] Write a reflection (higher-order insight)."""
        return self._write(role_id, persona_id, "reflection", content, importance, embedding)

    def write_commitment(
        self,
        role_id: str,
        persona_id: str,
        content: str,
        importance: float = 0.8,
        embedding: list[float] | None = None,
    ) -> str:
        """Write a user commitment/promise memory."""
        return self._write(role_id, persona_id, "commitment", content, importance, embedding)

    def retrieve_top_k(
        self,
        role_id: str,
        persona_id: str,
        query: str | None = None,
        query_embedding: list[float] | None = None,
        k: int = 5,
    ) -> list[Memory]:
        """
        [R11 ss3.2] Retrieve top-k memories by composite score.
        score = alpha * recency + beta * importance + gamma * relevance
        [RISK-06] Strictly filtered by (role_id, persona_id).
        """
        now = time.time()
        candidates = [
            m for m in self._memories.values()
            if m.role_id == role_id and m.persona_id == persona_id
        ]

        scored: list[tuple[float, Memory]] = []
        for m in candidates:
            hours_ago = (now - m.created_at) / 3600.0
            recency = RECENCY_DECAY ** hours_ago

            relevance = 0.5  # default if no embedding
            if query_embedding and m.embedding:
                relevance = _cosine_similarity(query_embedding, m.embedding)

            score = (
                ALPHA_RECENCY * recency
                + BETA_IMPORTANCE * m.importance
                + GAMMA_RELEVANCE * relevance
            )
            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Update last_accessed
        results = []
        for _, m in scored[:k]:
            m.last_accessed = now
            results.append(m)
        return results

    def get_all(self, role_id: str, persona_id: str) -> list[Memory]:
        """Get all memories for a (role_id, persona_id) pair."""
        return [
            m for m in self._memories.values()
            if m.role_id == role_id and m.persona_id == persona_id
        ]

    def _write(
        self,
        role_id: str,
        persona_id: str,
        kind: str,
        content: str,
        importance: float,
        embedding: list[float] | None,
    ) -> str:
        mid = str(uuid.uuid4())
        now = time.time()
        mem = Memory(
            id=mid,
            role_id=role_id,
            persona_id=persona_id,
            kind=kind,
            content=content,
            importance=max(0.0, min(1.0, importance)),
            created_at=now,
            last_accessed=now,
            embedding=embedding,
        )
        self._memories[mid] = mem
        return mid


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def estimate_token_count(text: str) -> int:
    """Rough token estimate for CJK-heavy text (~1.5 chars per token)."""
    return max(1, int(len(text) / 1.5))
"""
"""
