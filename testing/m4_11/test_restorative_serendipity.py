import json
from pathlib import Path
import pytest
from m4_11_zpd_pipeline.schemas import TaskDifficulty, TaskType
from m4_11_zpd_pipeline.task_synthesizer import TaskSynthesizer
from m4_11_zpd_pipeline.zone_sampler import ZoneSampler


def test_restorative_seeds_count():
    """Verify that seeds.json contains at least 15 restorative real-world tasks (T031)."""
    seeds_path = Path(__file__).resolve().parent.parent.parent / "services" / "m4_11_zpd_pipeline" / "seeds.json"
    with open(seeds_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)

    real_world_seeds = [
        s for s in seeds
        if s.get("task_type") == TaskType.RESTORATIVE_SERENDIPITY.value and s.get("is_real_world") is True
    ]
    assert len(real_world_seeds) >= 15


def test_adaptive_fatigue_boost_distribution():
    """
    Verify that in normal conditions, restorative tasks appear ~15% (10%~25%),
    and in fatigue/anxious conditions, adaptively boosts to 50%~80% (nominal 70%) (T029, T030).
    """
    sampler = ZoneSampler()
    trials = 1000

    # 1. Normal state
    normal_restorative_count = sum(
        1 for _ in range(trials)
        if sampler.sample(p_mastery=0.5, cognitive_load="normal", is_anxious=False).task_type
        == TaskType.RESTORATIVE_SERENDIPITY
    )
    normal_ratio = normal_restorative_count / trials
    assert 0.10 <= normal_ratio <= 0.25, f"Normal ratio {normal_ratio} outside 10%~25%"

    # 2. Fatigue / Anxious state
    fatigue_restorative_count = sum(
        1 for _ in range(trials)
        if sampler.sample(p_mastery=0.5, cognitive_load="high", is_anxious=True).task_type
        == TaskType.RESTORATIVE_SERENDIPITY
    )
    fatigue_ratio = fatigue_restorative_count / trials
    assert 0.55 <= fatigue_ratio <= 0.85, f"Fatigue ratio {fatigue_ratio} outside 55%~85%"


def test_restorative_synthesized_invariants():
    """Verify that synthesized restorative serendipity tasks satisfy all invariants (T032)."""
    synthesizer = TaskSynthesizer()
    task = synthesizer.synthesize_fallback(
        user_id="user_zen",
        role_id="role_csie",
        preferred_task_type=TaskType.RESTORATIVE_SERENDIPITY,
        preferred_difficulty=TaskDifficulty.RESTORATIVE,
    )

    assert task["task_type"] == TaskType.RESTORATIVE_SERENDIPITY.value
    assert task["is_real_world"] is True
    assert task["estimated_minutes"] <= 20
    assert task["difficulty"] == TaskDifficulty.RESTORATIVE.value
    assert task["zpd_zone"] == "restorative_haven"
    assert len(task["scaffolding_hints"]) >= 1
