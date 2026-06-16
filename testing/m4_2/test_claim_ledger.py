"""
P3 Claim Ledger -- test suite

Research: [R03 ss2] ARPM [R14] RoleLLM/RoleBench
Risk: RISK-02
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_2_persona.claim_ledger import (
    ClaimLedger,
    generate_persona_quiz,
)


class TestClaimExtraction:
    """[R03 ss2] Factual claim extraction from responses."""

    def test_claim_extraction_from_response(self):
        """Extract year claims from a persona response."""
        ledger = ClaimLedger()
        claims = ledger.extract_claims(
            "I was born in 1992 and graduated in 2016 from NTHU."
        )
        years = [c for c in claims if c.category == "year"]
        assert len(years) >= 2
        year_texts = {c.text for c in years}
        assert "1992" in year_texts
        assert "2016" in year_texts

    def test_claim_extraction_numbers(self):
        """Extract number claims with context."""
        ledger = ClaimLedger()
        claims = ledger.extract_claims("I worked there for 8 years before switching.")
        nums = [c for c in claims if c.category == "number"]
        assert any(c.text == "8" for c in nums)


class TestContradictionDetection:
    """[R03 ss2] Detecting persona drift via contradictions."""

    def test_contradiction_detection(self):
        """Conflicting year claims from different turns should be detected."""
        ledger = ClaimLedger()
        ledger.extract_claims("I was born in 1992.")
        ledger.extract_claims("I was born in 1988.")
        events = ledger.check_contradictions()
        assert len(events) >= 1
        assert "1992" in events[0].contradiction_reason
        assert "1988" in events[0].contradiction_reason

    def test_no_contradiction_same_facts(self):
        """Consistent claims should not trigger drift."""
        ledger = ClaimLedger()
        ledger.extract_claims("I was born in 1992.")
        ledger.extract_claims("In 1992, I was born.")
        events = ledger.check_contradictions()
        assert len(events) == 0


class TestDriftEventLogging:
    """[RISK-02] Drift detection behavior."""

    def test_drift_event_logged(self):
        """Drift events should be logged but not raise exceptions."""
        ledger = ClaimLedger()
        ledger.extract_claims("Born in 1992.")
        ledger.extract_claims("Born in 1988.")
        ledger.check_contradictions()
        assert ledger.has_drift
        assert len(ledger.drift_events) >= 1

    def test_no_conversation_interruption(self):
        """Drift detection should never raise or block."""
        ledger = ClaimLedger()
        # Even with contradictions, no exception should be raised
        ledger.extract_claims("Born in 1992.")
        ledger.extract_claims("Born in 1985.")
        try:
            ledger.check_contradictions()
        except Exception:
            pytest.fail("Contradiction check should never raise")


class TestPersonaQuizGeneration:
    """[R14] RoleBench-style persona quiz."""

    def test_persona_quiz_generation(self):
        """Generate identity quiz from PersonaCard dict."""
        card_dict = {
            "identity": {"name": "Robert", "birth_year": 1992, "education": "NTHU CS", "career": "Systems Engineer"},
            "big_five": {"O": 0.6, "C": 0.8, "E": 0.4, "A": 0.5, "N": 0.3},
            "knowledge_boundary": {"expert_in": ["Linux"], "ignorant_of": ["medicine"]},
            "stances": [{"topic": "TDD", "position": "non-negotiable"}],
            "formative_episodes": [{"age": 25, "event": "Led migration project"}],
        }
        questions = generate_persona_quiz(card_dict, count=20)
        assert len(questions) >= 5
        # Should have identity questions
        assert any("name" in q["question"].lower() for q in questions)
        # Should have knowledge boundary questions
        assert any("medicine" in q["question"].lower() for q in questions)

    def test_quiz_count_cap(self):
        """Quiz should not exceed requested count."""
        card_dict = {
            "identity": {"name": "Test", "birth_year": 2000, "education": "MIT", "career": "Dev"},
            "big_five": {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5},
            "knowledge_boundary": {"expert_in": ["a", "b", "c"], "ignorant_of": ["x", "y", "z"]},
            "stances": [{"topic": "t1", "position": "p1"}, {"topic": "t2", "position": "p2"}],
            "formative_episodes": [{"age": 20, "event": "e1"}, {"age": 25, "event": "e2"}],
        }
        questions = generate_persona_quiz(card_dict, count=5)
        assert len(questions) <= 5
"""
"""
