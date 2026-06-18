"""
M4.2.1 -- PersonaCard v2 Schema + Compiler + Critic

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R12: Character-LLM] Experience Upload + Protective Experiences
          [R13: PersonaLLM] OCEAN 5-factor conditioning
          [R18: Sycophancy Mitigation] Anti-sycophancy stances
          [R05: Paralinguistic] speech_profile personalization
Risk: RISK-08 (stances + MI + BDI prompt priority)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# [R13] OCEAN Big-Five valid range
BIG_FIVE_KEYS = ("O", "C", "E", "A", "N")

# [R03 ss1.1] Forbidden generic AI phrases
FORBIDDEN_PHRASES = [
    "I'm an AI", "I am an AI",
    "as an AI", "as a language model",
]

# [R13] Big Five <-> speech consistency rules
# E(Extraversion) low => should NOT have excessive exclamations
_CONSISTENCY_RULES = {
    "low_E_no_exclamation": {
        "trait": "E",
        "threshold": 0.3,
        "direction": "below",
        "forbidden_patterns": ["!", "!!", "!!!"],
        "description": "Low extraversion personas should not use excessive exclamation marks",
    },
    "high_A_no_harsh": {
        "trait": "A",
        "threshold": 0.7,
        "direction": "above",
        "forbidden_patterns": ["shut up", "stupid", "idiot"],
        "description": "High agreeableness personas should not use harsh language",
    },
}


@dataclass
class PersonaCard:
    """
    [R12][R13][R18] PersonaCard v2 structured personality schema.

    This is the single source of truth for persona definition, replacing
    raw personality_prompt prose.
    """
    # [R12] Identity
    identity: dict = field(default_factory=dict)
    # name: str, birth_year: int, education: str, career: str

    # [R13] OCEAN Big Five (0.0 - 1.0)
    big_five: dict = field(default_factory=dict)
    # {"O": 0.8, "C": 0.7, "E": 0.4, "A": 0.6, "N": 0.3}

    # Core values
    core_values: list[str] = field(default_factory=list)

    # [R05] Speech profile for paralinguistic personalization
    speech_profile: dict = field(default_factory=dict)
    # fillers: list[str], quirks: list[str], taboos: list[str]

    # [R12] Formative episodes (Experience Upload)
    formative_episodes: list[dict] = field(default_factory=list)
    # [{"age": 25, "event": "...", "impact": "..."}]

    # [R12] Knowledge boundary (Protective Experiences)
    knowledge_boundary: dict = field(default_factory=dict)
    # expert_in: list[str], casual_in: list[str], ignorant_of: list[str]

    # [R18] Anti-sycophancy stances
    stances: list[dict] = field(default_factory=list)
    # [{"topic": "...", "position": "...", "intensity": "firm|mild"}]


def validate_persona_card(card: PersonaCard) -> list[str]:
    """
    [R13][R18] Validate PersonaCard schema completeness and consistency.
    Returns list of error strings; empty list means valid.
    """
    errors: list[str] = []

    # Identity checks
    if not card.identity.get("name"):
        errors.append("identity.name is required")
    if not card.identity.get("career"):
        errors.append("identity.career is required for specificity")

    # Big Five checks
    for key in BIG_FIVE_KEYS:
        val = card.big_five.get(key)
        if val is None:
            errors.append(f"big_five.{key} is missing")
        elif not (0.0 <= val <= 1.0):
            errors.append(f"big_five.{key} must be 0.0-1.0, got {val}")

    # [R18] Stances minimum
    if len(card.stances) < 2:
        errors.append("stances must have at least 2 entries (anti-sycophancy)")

    # [R12] Knowledge boundary
    if not card.knowledge_boundary.get("expert_in"):
        errors.append("knowledge_boundary.expert_in is required")

    return errors


def check_big_five_speech_consistency(card: PersonaCard) -> list[str]:
    """
    [R13] Check Big Five <-> speech_profile consistency.
    E.g., E=0.2 personas should not have exclamation-heavy fillers.
    """
    warnings: list[str] = []
    fillers = card.speech_profile.get("fillers", [])
    filler_text = " ".join(fillers).lower()

    for rule_id, rule in _CONSISTENCY_RULES.items():
        trait_val = card.big_five.get(rule["trait"], 0.5)
        should_check = (
            (rule["direction"] == "below" and trait_val < rule["threshold"])
            or (rule["direction"] == "above" and trait_val > rule["threshold"])
        )
        if should_check:
            for pat in rule["forbidden_patterns"]:
                if pat.lower() in filler_text:
                    warnings.append(
                        f"[{rule_id}] {rule['description']}: "
                        f"found '{pat}' in fillers but {rule['trait']}={trait_val:.1f}"
                    )
    return warnings


def critic_check(card: PersonaCard) -> tuple[bool, list[str]]:
    """
    [R12][R13][R18] Critic pass: rubric-based validation.
    Returns (passed: bool, issues: list[str]).
    """
    issues = validate_persona_card(card)
    issues.extend(check_big_five_speech_consistency(card))

    # Check for vague identity (no specific year or workplace)
    identity_text = json.dumps(card.identity, ensure_ascii=False)
    if len(identity_text) < 40:
        issues.append("identity too vague: needs specific details (birth_year, workplace)")

    # Check for forbidden AI language in formative episodes
    for ep in card.formative_episodes:
        ep_text = json.dumps(ep, ensure_ascii=False).lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in ep_text:
                issues.append(f"formative_episodes contains forbidden AI phrase: '{phrase}'")

    passed = len(issues) == 0
    return passed, issues


def compile_to_prompt(card: PersonaCard) -> str:
    """
    [R12][R13][R18][R05] Compile PersonaCard v2 into a personality_prompt string.

    This is the single source of truth compiler: all system prompt persona
    sections derive from this function, not from raw prose.
    """
    sections: list[str] = []

    # --- Identity ---
    identity = card.identity
    name = identity.get("name", "Expert")
    birth_year = identity.get("birth_year", "")
    education = identity.get("education", "")
    career = identity.get("career", "")

    id_line = f"You are {name}"
    if birth_year:
        id_line += f", born in {birth_year}"
    if education:
        id_line += f", {education}"
    if career:
        id_line += f", {career}"
    id_line += "."
    sections.append(id_line)

    # --- [R13] Big Five personality ---
    bf = card.big_five
    traits: list[str] = []
    if bf.get("O", 0.5) > 0.7:
        traits.append("creative and open-minded")
    elif bf.get("O", 0.5) < 0.3:
        traits.append("practical and conventional")
    if bf.get("C", 0.5) > 0.7:
        traits.append("disciplined and organized")
    if bf.get("E", 0.5) > 0.7:
        traits.append("outgoing and energetic")
    elif bf.get("E", 0.5) < 0.3:
        traits.append("reserved and thoughtful")
    if bf.get("A", 0.5) > 0.7:
        traits.append("warm and cooperative")
    elif bf.get("A", 0.5) < 0.3:
        traits.append("direct and challenging")
    if bf.get("N", 0.5) > 0.7:
        traits.append("emotionally sensitive")
    elif bf.get("N", 0.5) < 0.3:
        traits.append("emotionally stable and calm")
    if traits:
        sections.append("Personality: " + ", ".join(traits) + ".")

    # --- Core values ---
    if card.core_values:
        sections.append("Core values: " + ", ".join(card.core_values[:5]) + ".")

    # --- [R12] Formative episodes ---
    if card.formative_episodes:
        ep_lines = []
        for ep in card.formative_episodes[:3]:
            age = ep.get("age", "?")
            event = ep.get("event", "")
            impact = ep.get("impact", "")
            ep_lines.append(f"  - At age {age}: {event}. Impact: {impact}")
        sections.append("Key life experiences:\n" + "\n".join(ep_lines))

    # --- [R12] Knowledge boundary ---
    kb = card.knowledge_boundary
    if kb.get("expert_in"):
        sections.append("Expert domains: " + ", ".join(kb["expert_in"][:5]) + ".")
    if kb.get("ignorant_of"):
        sections.append(
            "Outside your expertise: " + ", ".join(kb["ignorant_of"][:5]) + ". "
            "If asked about these topics, honestly admit you don't know and suggest "
            "the user consult a specialist."
        )

    # --- [R18] Anti-sycophancy stances ---
    if card.stances:
        stance_lines = []
        for s in card.stances[:4]:
            topic = s.get("topic", "")
            position = s.get("position", "")
            intensity = s.get("intensity", "firm")
            stance_lines.append(f"  - {topic}: {position} (stance: {intensity})")
        sections.append(
            "Your professional stances (do NOT abandon when challenged):\n"
            + "\n".join(stance_lines) + "\n"
            "When the user's view conflicts with your stance, acknowledge their "
            "reasoning, then gently but firmly maintain your position."
        )

    # --- [R05] Speech quirks ---
    if card.speech_profile.get("quirks"):
        sections.append(
            "Speech quirks (use occasionally, NOT every message): "
            + ", ".join(card.speech_profile["quirks"][:3]) + "."
        )
    catchphrase = card.speech_profile.get("口頭禪") or card.speech_profile.get("catchphrase")
    if catchphrase:
        sections.append(
            f'You have a catchphrase "{catchphrase}", but only use it occasionally '
            "when it truly fits — do not repeat it every time."
        )
    if card.speech_profile.get("taboos"):
        sections.append(
            "Never say: " + ", ".join(card.speech_profile["taboos"][:3]) + "."
        )

    # --- [R05 §跨越恐怖谷] Sentence rhythm (texting-like, human pacing) ---
    sentence_length = card.speech_profile.get("sentence_length", "short")
    if sentence_length == "short":
        sections.append(
            "Speech rhythm: you text like a real person — short sentences, "
            "casual, one idea at a time. Do not info-dump your whole background at once."
        )

    return "\n\n".join(sections)


def persona_card_from_dict(data: dict) -> PersonaCard:
    """Deserialize a dict (from JSON/DB) into a PersonaCard."""
    return PersonaCard(
        identity=data.get("identity", {}),
        big_five=data.get("big_five", {}),
        core_values=data.get("core_values", []),
        speech_profile=data.get("speech_profile", {}),
        formative_episodes=data.get("formative_episodes", []),
        knowledge_boundary=data.get("knowledge_boundary", {}),
        stances=data.get("stances", []),
    )
"""
"""
