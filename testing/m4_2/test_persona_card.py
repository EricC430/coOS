"""
P1 PersonaCard v2 -- test suite

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R12] Character-LLM [R13] PersonaLLM [R18] Sycophancy Mitigation
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_2_persona.persona_card import (
    PersonaCard,
    check_big_five_speech_consistency,
    compile_to_prompt,
    critic_check,
    persona_card_from_dict,
    validate_persona_card,
)


def _make_valid_card(**overrides) -> PersonaCard:
    """Helper: build a minimal valid PersonaCard."""
    defaults = dict(
        identity={"name": "Robert", "birth_year": 1992, "education": "NTHU CS MS", "career": "TSMC 8yr systems engineer"},
        big_five={"O": 0.6, "C": 0.8, "E": 0.4, "A": 0.5, "N": 0.3},
        core_values=["precision", "mentorship"],
        speech_profile={"fillers": ["hmm...", "let me think"], "quirks": ["uses Socratic questions"], "taboos": ["I'm an AI"]},
        formative_episodes=[
            {"age": 25, "event": "Led migration of TSMC fab monitoring system", "impact": "Learned to handle pressure"},
            {"age": 30, "event": "Mentored 3 junior engineers through burnout", "impact": "Developed coaching style"},
        ],
        knowledge_boundary={"expert_in": ["systems engineering", "Linux"], "casual_in": ["web dev"], "ignorant_of": ["medical diagnosis"]},
        stances=[
            {"topic": "test-driven development", "position": "TDD is non-negotiable for production code", "intensity": "firm"},
            {"topic": "premature optimization", "position": "Profile first, optimize later", "intensity": "mild"},
        ],
    )
    defaults.update(overrides)
    return PersonaCard(**defaults)


class TestPersonaCardSchema:
    """[R12][R13] PersonaCard v2 schema validation."""

    def test_persona_card_schema_validation(self):
        """Valid PersonaCard passes validation with no errors."""
        card = _make_valid_card()
        errors = validate_persona_card(card)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_missing_name_fails(self):
        """identity.name missing should fail."""
        card = _make_valid_card(identity={"career": "engineer"})
        errors = validate_persona_card(card)
        assert any("identity.name" in e for e in errors)

    def test_missing_big_five_key_fails(self):
        """Missing OCEAN key should fail."""
        card = _make_valid_card(big_five={"O": 0.5, "C": 0.5})
        errors = validate_persona_card(card)
        assert any("big_five.E" in e for e in errors)

    def test_big_five_out_of_range_fails(self):
        """Big Five value outside [0.0, 1.0] should fail."""
        card = _make_valid_card(big_five={"O": 1.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5})
        errors = validate_persona_card(card)
        assert any("must be 0.0-1.0" in e for e in errors)


class TestPersonaCardCritic:
    """[R12][R13][R18] Critic pass validation."""

    def test_compiler_critic_rejects_vague(self):
        """Vague identity (too short) should be rejected by critic."""
        card = _make_valid_card(identity={"name": "X", "career": "?"})
        passed, issues = critic_check(card)
        assert not passed
        assert any("vague" in i.lower() for i in issues)

    def test_stances_minimum_two(self):
        """PersonaCard with < 2 stances should fail validation."""
        card = _make_valid_card(stances=[{"topic": "TDD", "position": "good", "intensity": "firm"}])
        errors = validate_persona_card(card)
        assert any("stances must have at least 2" in e for e in errors)

    def test_valid_card_passes_critic(self):
        """Fully valid PersonaCard passes critic."""
        card = _make_valid_card()
        passed, issues = critic_check(card)
        assert passed, f"Critic failed with: {issues}"

    def test_forbidden_ai_phrase_in_episodes(self):
        """Formative episodes containing AI phrases should fail critic."""
        card = _make_valid_card(
            formative_episodes=[{"age": 25, "event": "I'm an AI assistant", "impact": "none"}]
        )
        passed, issues = critic_check(card)
        assert not passed
        assert any("forbidden AI phrase" in i for i in issues)


class TestBigFiveSpeechConsistency:
    """[R13] Big Five <-> speech profile consistency."""

    def test_low_e_no_exclamation(self):
        """E=0.2 persona with exclamation-heavy fillers should warn."""
        card = _make_valid_card(
            big_five={"O": 0.5, "C": 0.5, "E": 0.2, "A": 0.5, "N": 0.5},
            speech_profile={"fillers": ["Wow!", "Amazing!!"], "quirks": [], "taboos": []},
        )
        warnings = check_big_five_speech_consistency(card)
        assert len(warnings) > 0
        assert any("exclamation" in w.lower() for w in warnings)

    def test_consistent_profile_no_warning(self):
        """Consistent Big Five + speech profile should produce no warnings."""
        card = _make_valid_card()
        warnings = check_big_five_speech_consistency(card)
        assert warnings == []


class TestCompileToPrompt:
    """[R12][R13][R18] PersonaCard -> prompt compilation."""

    def test_knowledge_boundary_injection(self):
        """ignorant_of domains should trigger 'don't know' directive in prompt."""
        card = _make_valid_card()
        prompt = compile_to_prompt(card)
        assert "honestly admit" in prompt.lower() or "don't know" in prompt.lower()
        assert "medical diagnosis" in prompt

    def test_anti_sycophancy_stance_injection(self):
        """Stances should be injected with 'do NOT abandon' directive."""
        card = _make_valid_card()
        prompt = compile_to_prompt(card)
        assert "do NOT abandon" in prompt or "NOT abandon" in prompt
        assert "TDD" in prompt or "test-driven" in prompt.lower()

    def test_identity_in_prompt(self):
        """Compiled prompt contains identity details."""
        card = _make_valid_card()
        prompt = compile_to_prompt(card)
        assert "Robert" in prompt
        assert "1992" in prompt

    def test_formative_episodes_in_prompt(self):
        """Formative episodes should appear in prompt."""
        card = _make_valid_card()
        prompt = compile_to_prompt(card)
        assert "TSMC" in prompt
        assert "mentored" in prompt.lower() or "Mentored" in prompt

    def test_speech_quirks_in_prompt(self):
        """Speech quirks should be in prompt."""
        card = _make_valid_card()
        prompt = compile_to_prompt(card)
        assert "Socratic" in prompt


class TestPersonaCardSerialization:
    """PersonaCard dict serialization roundtrip."""

    def test_from_dict_roundtrip(self):
        """persona_card_from_dict correctly deserializes."""
        data = {
            "identity": {"name": "Test", "career": "Dev"},
            "big_five": {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5},
            "core_values": ["honesty"],
            "speech_profile": {"fillers": ["um"]},
            "formative_episodes": [],
            "knowledge_boundary": {"expert_in": ["coding"]},
            "stances": [{"topic": "a", "position": "b"}, {"topic": "c", "position": "d"}],
        }
        card = persona_card_from_dict(data)
        assert card.identity["name"] == "Test"
        assert card.big_five["O"] == 0.5
        assert len(card.stances) == 2
"""
"""
