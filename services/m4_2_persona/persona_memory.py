"""
M4.2.2 -- Persona Episodic Memory Store (SQLite-backed)

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R11: Park et al. ss3.2] Retrieval scoring = recency x importance x relevance
          [R15: MemGPT ss Memory Management] Tiered memory, token budget <= 350
          [R19: sqlite-vec] Local vector search (future)
Risk: RISK-06 (role_id, persona_id double-key isolation)
      RISK-12 (PII masking before write)
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

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


def _iso_to_ts(iso_str: str) -> float:
    """Parse ISO timestamp to unix timestamp."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, AttributeError):
        return time.time()


def _ts_to_iso(ts: float) -> str:
    """Convert unix timestamp to ISO string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PersonaMemoryStore:
    """
    [R11][R15][R19] (role_id, persona_id) double-key isolated episodic memory.

    Persists to local SQLite (L1 privacy tier).
    PII must be masked before calling write_* methods.
    """

    def __init__(self, db_path: str | None = None):
        from m6_1_sqlite.init import open_sqlite
        self._conn = open_sqlite(db_path)

    def write_observation(
        self,
        role_id: str,
        persona_id: str,
        content: str,
        importance: float = 0.5,
        embedding: list[float] | None = None,
    ) -> str:
        """[R11 ss3.1] Write an observation memory."""
        return self._write(role_id, persona_id, "observation", content, importance)

    def write_reflection(
        self,
        role_id: str,
        persona_id: str,
        content: str,
        importance: float = 0.7,
        embedding: list[float] | None = None,
    ) -> str:
        """[R11 ss3.3] Write a reflection (higher-order insight)."""
        return self._write(role_id, persona_id, "reflection", content, importance)

    def write_commitment(
        self,
        role_id: str,
        persona_id: str,
        content: str,
        importance: float = 0.8,
        embedding: list[float] | None = None,
    ) -> str:
        """Write a user commitment/promise memory."""
        return self._write(role_id, persona_id, "commitment", content, importance)

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
        cursor = self._conn.execute(
            "SELECT id, role_id, persona_id, kind, content, importance, "
            "created_at, last_accessed_at "
            "FROM persona_episodic_memories "
            "WHERE role_id = ? AND persona_id = ? "
            "ORDER BY created_at DESC LIMIT 50",
            (role_id, persona_id),
        )
        rows = cursor.fetchall()

        scored: list[tuple[float, Memory]] = []
        for row in rows:
            created_ts = _iso_to_ts(row["created_at"])
            hours_ago = max(0.0, (now - created_ts) / 3600.0)
            recency = RECENCY_DECAY ** hours_ago

            relevance = 0.5  # default without embedding
            if query_embedding:
                pass  # future: sqlite-vec cosine similarity

            importance_val = row["importance"] or 0.5
            score = (
                ALPHA_RECENCY * recency
                + BETA_IMPORTANCE * importance_val
                + GAMMA_RELEVANCE * relevance
            )

            mem = Memory(
                id=row["id"],
                role_id=row["role_id"],
                persona_id=row["persona_id"],
                kind=row["kind"],
                content=row["content"],
                importance=importance_val,
                created_at=created_ts,
                last_accessed=_iso_to_ts(row["last_accessed_at"]),
            )
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for _, m in scored[:k]:
            self._conn.execute(
                "UPDATE persona_episodic_memories SET last_accessed_at = ? WHERE id = ?",
                (_ts_to_iso(now), m.id),
            )
            m.last_accessed = now
            results.append(m)
        if results:
            self._conn.commit()

        return results

    def get_all(self, role_id: str, persona_id: str) -> list[Memory]:
        """Get all memories for a (role_id, persona_id) pair."""
        cursor = self._conn.execute(
            "SELECT id, role_id, persona_id, kind, content, importance, "
            "created_at, last_accessed_at "
            "FROM persona_episodic_memories "
            "WHERE role_id = ? AND persona_id = ? "
            "ORDER BY created_at DESC",
            (role_id, persona_id),
        )
        return [
            Memory(
                id=row["id"],
                role_id=row["role_id"],
                persona_id=row["persona_id"],
                kind=row["kind"],
                content=row["content"],
                importance=row["importance"] or 0.5,
                created_at=_iso_to_ts(row["created_at"]),
                last_accessed=_iso_to_ts(row["last_accessed_at"]),
            )
            for row in cursor.fetchall()
        ]

    def _write(
        self,
        role_id: str,
        persona_id: str,
        kind: str,
        content: str,
        importance: float,
    ) -> str:
        mid = str(uuid.uuid4())
        now_iso = _ts_to_iso(time.time())
        self._conn.execute(
            "INSERT INTO persona_episodic_memories "
            "(id, role_id, persona_id, kind, content, importance, created_at, last_accessed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (mid, role_id, persona_id, kind, content,
             max(0.0, min(1.0, importance)), now_iso, now_iso),
        )
        self._conn.commit()
        return mid


# --- Singleton for graph usage ---
_store: PersonaMemoryStore | None = None


def get_memory_store(db_path: str | None = None) -> PersonaMemoryStore:
    """Get or create the singleton PersonaMemoryStore."""
    global _store
    if _store is None:
        _store = PersonaMemoryStore(db_path)
    return _store


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
