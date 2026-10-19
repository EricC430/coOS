import pytest
from m4_11_zpd_pipeline.schemas import TaskDifficulty, TaskType
from m4_11_zpd_pipeline.zone_sampler import ZoneSampler


def test_zone_sampler_normal_distribution():
    sampler = ZoneSampler()
    # Mastery in middle range
    p_mastery = 0.50

    sampled_difficulties = []
    for _ in range(100):
        decision = sampler.sample(
            p_mastery=p_mastery,
            cognitive_load="normal",
            is_anxious=False,
        )
        sampled_difficulties.append(decision.difficulty)

    assert TaskDifficulty.JUST_MANAGEABLE in sampled_difficulties
    assert TaskDifficulty.COMFORT in sampled_difficulties
    assert TaskDifficulty.STRETCH in sampled_difficulties


def test_zone_sampler_safety_retraction_on_anxiety():
    """
    [RISK-09] When anxiety or high cognitive fatigue is detected,
    stretch difficulty must be 100% eliminated, duration capped at <= 15 min.
    """
    sampler = ZoneSampler()
    p_mastery = 0.85  # Even if user has high mastery

    for _ in range(50):
        decision = sampler.sample(
            p_mastery=p_mastery,
            cognitive_load="high",
            is_anxious=True,
        )
        # In anxious state, stretch is forbidden
        assert decision.difficulty != TaskDifficulty.STRETCH
        assert decision.max_minutes <= 15
        assert decision.is_safety_retracted is True
