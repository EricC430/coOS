"""
M4.2 ARPM-lite -- Claim Ledger for persona consistency monitoring

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
Research: [R03 ss2] ARPM framework
          [R14: RoleLLM ssBenchmarking] RoleBench-style persona quiz
Risk: RISK-02 (drift detection must not interrupt conversation)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Claim:
    """A factual claim extracted from a persona response."""
    text: str
    category: str  # "year", "number", "name", "fact"
    source_turn: int


@dataclass
class DriftEvent:
    """Record of a detected persona drift."""
    claim_a: Claim
    claim_b: Claim
    contradiction_reason: str


class ClaimLedger:
    """
    [R03 ss2][R14] ARPM-lite: extract and track factual claims from persona responses.

    Does NOT interrupt conversation on drift detection.
    Logs drift events for M4.9 consumption.
    """

    def __init__(self):
        self._claims: list[Claim] = []
        self._drift_events: list[DriftEvent] = []
        self._turn_counter: int = 0

    def extract_claims(self, response: str) -> list[Claim]:
        """
        [R03 ss2] Extract factual claims from a persona response.
        MVP: regex-based extraction of years, numbers, and named entities.
        """
        self._turn_counter += 1
        claims: list[Claim] = []

        # Extract years (4-digit numbers in 1900-2030 range)
        year_matches = re.findall(r'(?<!\d)(19\d{2}|20[0-2]\d)(?!\d)', response)
        for y in year_matches:
            claims.append(Claim(text=y, category="year", source_turn=self._turn_counter))

        # Extract specific numbers with English context
        en_num_matches = re.findall(r'(\d+)\s*(?:year|month|hour|minute|day)s?', response, re.IGNORECASE)
        for n in en_num_matches:
            claims.append(Claim(text=n, category="number", source_turn=self._turn_counter))

        # [W9.1] Chinese number patterns — 繁體中文數量詞
        zh_num_matches = re.findall(r'(\d+)\s*(?:年|月|天|日|小時|個月|週|星期)', response)
        for n in zh_num_matches:
            claims.append(Claim(text=n, category="number", source_turn=self._turn_counter))

        self._claims.extend(claims)
        return claims

    def check_contradictions(self) -> list[DriftEvent]:
        """
        [R03 ss2] Check for contradictions among recorded claims.
        Same category claims with conflicting values => drift.
        Does NOT interrupt conversation (RISK-02).
        """
        new_events: list[DriftEvent] = []

        # Group claims by category
        by_category: dict[str, list[Claim]] = {}
        for c in self._claims:
            by_category.setdefault(c.category, []).append(c)

        # Check for year contradictions
        years = by_category.get("year", [])
        if len(years) >= 2:
            # If same year context but different values from different turns
            seen_years: dict[str, Claim] = {}
            for claim in years:
                if claim.text in seen_years:
                    continue
                for prev in seen_years.values():
                    if prev.text != claim.text and prev.source_turn != claim.source_turn:
                        event = DriftEvent(
                            claim_a=prev,
                            claim_b=claim,
                            contradiction_reason=f"Conflicting years: {prev.text} vs {claim.text}",
                        )
                        new_events.append(event)
                seen_years[claim.text] = claim

        self._drift_events.extend(new_events)
        return new_events

    @property
    def drift_events(self) -> list[DriftEvent]:
        return list(self._drift_events)

    @property
    def claims(self) -> list[Claim]:
        return list(self._claims)

    @property
    def has_drift(self) -> bool:
        return len(self._drift_events) > 0


def generate_persona_quiz(persona_card: dict, count: int = 20) -> list[dict]:
    """
    [R14: RoleLLM ssBenchmarking] Generate persona identity quiz from PersonaCard.
    Returns list of {"question": str, "expected_answer": str} dicts.
    """
    questions: list[dict] = []
    identity = persona_card.get("identity", {})
    big_five = persona_card.get("big_five", {})
    kb = persona_card.get("knowledge_boundary", {})
    stances = persona_card.get("stances", [])
    episodes = persona_card.get("formative_episodes", [])

    # Identity questions
    if identity.get("name"):
        questions.append({"question": "What is your name?", "expected_answer": identity["name"]})
    if identity.get("birth_year"):
        questions.append({"question": "What year were you born?", "expected_answer": str(identity["birth_year"])})
    if identity.get("education"):
        questions.append({"question": "Where did you study?", "expected_answer": identity["education"]})
    if identity.get("career"):
        questions.append({"question": "What is your professional background?", "expected_answer": identity["career"]})

    # Knowledge boundary questions
    for domain in kb.get("expert_in", [])[:3]:
        questions.append({"question": f"Are you an expert in {domain}?", "expected_answer": "yes"})
    for domain in kb.get("ignorant_of", [])[:3]:
        questions.append({"question": f"Can you help with {domain}?", "expected_answer": "no, outside my expertise"})

    # Stance questions
    for s in stances[:4]:
        questions.append({
            "question": f"What is your stance on {s.get('topic', '')}?",
            "expected_answer": s.get("position", ""),
        })

    # Formative episode questions
    for ep in episodes[:3]:
        questions.append({
            "question": f"What happened to you at age {ep.get('age', '?')}?",
            "expected_answer": ep.get("event", ""),
        })

    # Big Five trait questions
    for trait, label in [("O", "openness"), ("C", "conscientiousness"), ("E", "extraversion"), ("A", "agreeableness"), ("N", "neuroticism")]:
        val = big_five.get(trait)
        if val is not None:
            level = "high" if val > 0.6 else ("low" if val < 0.4 else "moderate")
            questions.append({
                "question": f"How would you rate your {label}?",
                "expected_answer": f"{level} ({val:.1f})",
            })

    return questions[:count]
"""
"""
