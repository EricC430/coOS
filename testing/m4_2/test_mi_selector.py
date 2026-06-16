"""
P3 MI Selector -- test suite

Research: [R16] Motivational Interviewing [R09 ss4.1] SDT
Risk: RISK-02, RISK-03
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_2_persona.mi_selector import (
    MIDirective,
    MITechnique,
    SDTNeed,
    detect_change_talk,
    sdt_quick_check,
    select_mi_technique,
)


class TestMISelector:
    """[R16] MI technique selection based on user state."""

    def test_high_reactance_selects_reflective_listening(self):
        """Reactance > 0.7 -> reflective listening."""
        result = select_mi_technique(reactance_score=0.8)
        assert result.technique == MITechnique.REFLECTIVE_LISTENING
        assert "advice" in " ".join(result.forbidden_actions).lower()

    def test_anxiety_selects_affirmation_no_mirror(self):
        """[RISK-03] Anxiety -> affirmation, not mirroring."""
        result = select_mi_technique(reactance_score=0.3, implicit_state="anxiety")
        assert result.technique == MITechnique.AFFIRMATION
        assert "mirroring" in " ".join(result.forbidden_actions).lower() or \
               "mirror" in " ".join(result.forbidden_actions).lower()

    def test_avoidance_no_guilt(self):
        """[RISK-03] Avoidance -> open question, no guilt."""
        result = select_mi_technique(reactance_score=0.3, implicit_state="avoidance")
        assert result.technique == MITechnique.OPEN_QUESTION
        assert any("guilt" in f.lower() for f in result.forbidden_actions)

    def test_flow_selects_structured_advice(self):
        """Flow/stable -> structured advice."""
        result = select_mi_technique(reactance_score=0.1, implicit_state="flow")
        assert result.technique == MITechnique.STRUCTURED_ADVICE

    def test_change_talk_replay(self):
        """User expressing change intention -> replay."""
        result = select_mi_technique(
            reactance_score=0.2,
            user_message="I think I should start practicing more",
        )
        assert result.technique == MITechnique.CHANGE_TALK_REPLAY

    def test_reactance_overrides_change_talk(self):
        """High reactance should override change talk detection."""
        result = select_mi_technique(
            reactance_score=0.9,
            user_message="I should practice but you don't understand me",
        )
        assert result.technique == MITechnique.REFLECTIVE_LISTENING


class TestChangeTalkDetection:
    """[R16 ssChange Talk] Change talk marker detection."""

    def test_positive_detection(self):
        assert detect_change_talk("I think I should start studying earlier")

    def test_negative_detection(self):
        assert not detect_change_talk("The weather is nice today")


class TestSDTQuickCheck:
    """[R09 ss4.1] SDT need coverage in responses."""

    def test_sdt_quick_check(self):
        """Response touching autonomy/competence/relatedness."""
        response = "It's your choice how to approach this. You can do it, and we're in this together."
        needs = sdt_quick_check(response)
        assert SDTNeed.AUTONOMY in needs
        assert SDTNeed.COMPETENCE in needs
        assert SDTNeed.RELATEDNESS in needs

    def test_sdt_empty_response(self):
        needs = sdt_quick_check("Hello")
        assert needs == []

    def test_sdt_partial_coverage(self):
        response = "You've done great progress so far."
        needs = sdt_quick_check(response)
        assert SDTNeed.COMPETENCE in needs
"""
"""
