"""
P2 Persona Memory -- test suite

Research: [R11] Park et al. [R15] MemGPT [R19] sqlite-vec
Risk: RISK-06, RISK-12
"""
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_2_persona.persona_memory import (
    PersonaMemoryStore,
    estimate_token_count,
    _cosine_similarity,
)
from m4_2_persona.reflection_job import summarize_observations


class TestMemoryWriteAndRetrieve:
    """Basic read/write operations."""

    def test_memory_write_and_retrieve(self):
        store = PersonaMemoryStore()
        mid = store.write_observation("role_a", "expert_1", "User struggles with recursion", 0.7)
        assert mid
        results = store.retrieve_top_k("role_a", "expert_1", k=5)
        assert len(results) == 1
        assert results[0].content == "User struggles with recursion"

    def test_multiple_memories_ranked(self):
        store = PersonaMemoryStore()
        store.write_observation("r1", "e1", "low importance", 0.1)
        store.write_observation("r1", "e1", "high importance", 0.9)
        results = store.retrieve_top_k("r1", "e1", k=5)
        assert results[0].importance > results[-1].importance


class TestMemoryRoleIsolation:
    """[RISK-06] Double-key isolation."""

    def test_memory_role_isolation(self):
        store = PersonaMemoryStore()
        store.write_observation("role_csie", "expert_1", "CSIE memory")
        store.write_observation("role_family", "expert_1", "Family memory")

        csie_mems = store.retrieve_top_k("role_csie", "expert_1")
        family_mems = store.retrieve_top_k("role_family", "expert_1")

        assert len(csie_mems) == 1
        assert csie_mems[0].content == "CSIE memory"
        assert len(family_mems) == 1
        assert family_mems[0].content == "Family memory"

    def test_persona_isolation(self):
        store = PersonaMemoryStore()
        store.write_observation("r1", "expert_a", "Expert A memory")
        store.write_observation("r1", "expert_b", "Expert B memory")

        a_mems = store.retrieve_top_k("r1", "expert_a")
        b_mems = store.retrieve_top_k("r1", "expert_b")

        assert len(a_mems) == 1
        assert a_mems[0].content == "Expert A memory"
        assert len(b_mems) == 1


class TestMemoryPIIMasking:
    """[RISK-12] PII should be masked before write."""

    def test_memory_pii_masking(self):
        """Content written to store should already have PII masked by caller."""
        store = PersonaMemoryStore()
        # Simulate PII-masked content (caller responsibility)
        masked_content = "User [NAME] is working on project [PROJECT]"
        mid = store.write_observation("r1", "e1", masked_content, 0.5)
        results = store.retrieve_top_k("r1", "e1")
        assert "[NAME]" in results[0].content
        assert "real_name" not in results[0].content.lower()


class TestRetrievalScoringFormula:
    """[R11 ss3.2] Scoring: recency x importance x relevance."""

    def test_retrieval_scoring_formula(self):
        store = PersonaMemoryStore()
        # Write memories with different importance
        store.write_observation("r1", "e1", "Very important insight", 0.95)
        store.write_observation("r1", "e1", "Minor observation", 0.1)
        store.write_observation("r1", "e1", "Medium importance", 0.5)

        results = store.retrieve_top_k("r1", "e1", k=3)
        # Highest importance should rank first (recency is same, no embedding)
        assert results[0].importance == 0.95

    def test_cosine_similarity_identical(self):
        """Identical vectors should have similarity ~1.0."""
        sim = _cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        """Orthogonal vectors should have similarity ~0.0."""
        sim = _cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(sim) < 0.001


class TestReflectionSummarization:
    """[R11 ss3.3] Nightly reflection."""

    def test_reflection_summarizes_observations(self):
        observations = [
            {"content": "User solved 3 recursion problems", "importance": 0.8, "kind": "observation"},
            {"content": "User committed to finishing chapter 5", "importance": 0.7, "kind": "commitment"},
            {"content": "User mentioned feeling tired", "importance": 0.3, "kind": "observation"},
        ]
        reflections = summarize_observations(observations)
        assert len(reflections) >= 1
        assert len(reflections) <= 3
        # Top observation should appear in first reflection
        assert "recursion" in reflections[0].lower() or "insight" in reflections[0].lower()

    def test_empty_observations_no_reflection(self):
        reflections = summarize_observations([])
        assert reflections == []


class TestMemoryTokenBudget:
    """[R15] Token budget <= 350."""

    def test_memory_budget_350_tokens(self):
        store = PersonaMemoryStore()
        # Write 10 memories
        for i in range(10):
            store.write_observation("r1", "e1", f"Memory content number {i} with some detail", 0.5 + i * 0.05)

        results = store.retrieve_top_k("r1", "e1", k=5)
        combined = "\n".join(m.content for m in results)
        tokens = estimate_token_count(combined)
        assert tokens <= 350, f"Memory block is {tokens} tokens, exceeds 350"
"""
"""
