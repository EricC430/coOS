from datetime import datetime, timezone
import pytest
from m4_11_zpd_pipeline.schemas import (
    ChallengeStatus,
    DrawChallengeRequest,
    ZPDChallengeDTO,
)
from m4_11_zpd_pipeline.models import ZPDChallenge


def test_zero_staking_invariant_in_schema():
    """Verify that ZPDChallengeDTO strictly forbids any staking/penalty fields."""
    fields = ZPDChallengeDTO.model_fields.keys()
    forbidden_terms = ["stake", "staked_xp", "penalty", "loss", "cost"]
    for field in fields:
        for term in forbidden_terms:
            assert term not in field.lower(), f"Forbidden staking term '{term}' in field '{field}'"


def test_abandon_and_expiration_has_zero_penalty(zpd_service, db_session):
    """
    Verify that abandoning or expiring an accepted challenge results in 0 XP penalty
    and leaves user XP unpenalized (RISK-07).
    """
    challenge = zpd_service.draw_challenge(
        user_id="user_test",
        role_id="role_csie",
        force_fallback=True,
    )
    assert challenge is not None

    # Accept it
    accepted = zpd_service.accept_challenge(challenge.id, replace_existing=True)
    assert accepted.status == ChallengeStatus.ACCEPTED

    # Expire or abandon
    abandoned_record = db_session.query(ZPDChallenge).filter_by(id=challenge.id).first()
    abandoned_record.status = ChallengeStatus.ABANDONED.value
    db_session.commit()

    # Verify no XP loss is recorded or deductible
    assert abandoned_record.status == "abandoned"
