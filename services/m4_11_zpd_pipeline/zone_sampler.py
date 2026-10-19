import random
from dataclasses import dataclass
from typing import Optional

from .schemas import TaskDifficulty, TaskType


@dataclass
class SamplingDecision:
    task_type: TaskType
    difficulty: TaskDifficulty
    zpd_zone: str
    max_minutes: int
    is_safety_retracted: bool


class ZoneSampler:
    """
    ZONE Framework REJECT + GRAD Sampling & Safety Retraction Engine
    [R01: ZONE 框架 §理論基礎, RISK-09]
    """

    def __init__(self):
        pass

    def sample(
        self,
        p_mastery: float,
        cognitive_load: str = "normal",
        is_anxious: bool = False,
        force_task_type: Optional[TaskType] = None,
    ) -> SamplingDecision:
        """
        Execute dual-track sampling with anxiety safety retraction and cognitive fatigue adaptation.
        """
        is_fatigued = cognitive_load in ("high", "fatigued") or is_anxious

        # 1. Determine task type track
        if force_task_type:
            task_type = force_task_type
        else:
            # Under fatigue/anxiety, restorative serendipity probability boosts to 70% (US5)
            restorative_prob = 0.70 if is_fatigued else 0.15
            task_type = (
                TaskType.RESTORATIVE_SERENDIPITY
                if random.random() < restorative_prob
                else TaskType.SKILL_STRETCH
            )

        # 2. Determine difficulty & safety boundaries
        if task_type == TaskType.RESTORATIVE_SERENDIPITY:
            return SamplingDecision(
                task_type=TaskType.RESTORATIVE_SERENDIPITY,
                difficulty=TaskDifficulty.RESTORATIVE,
                zpd_zone="restorative_haven",
                max_minutes=15 if is_fatigued else 20,
                is_safety_retracted=is_fatigued,
            )

        # 3. Professional / Technical task track
        if is_fatigued:
            # [RISK-09] Anxiety Safety Retraction: stretch is 100% eliminated, max_minutes <= 15
            difficulty = random.choice([TaskDifficulty.COMFORT, TaskDifficulty.JUST_MANAGEABLE])
            return SamplingDecision(
                task_type=TaskType.SKILL_STRETCH,
                difficulty=difficulty,
                zpd_zone="core_zpd",
                max_minutes=15,
                is_safety_retracted=True,
            )

        # Normal condition: GRAD distribution
        # comfort (20%), just-manageable (60%), stretch (20%)
        roll = random.random()
        if roll < 0.20:
            difficulty = TaskDifficulty.COMFORT
            zone = "core_zpd"
            max_minutes = 20
        elif roll < 0.80:
            difficulty = TaskDifficulty.JUST_MANAGEABLE
            zone = "core_zpd"
            max_minutes = 30
        else:
            difficulty = TaskDifficulty.STRETCH
            zone = "upper_stretch"
            max_minutes = 45

        return SamplingDecision(
            task_type=TaskType.SKILL_STRETCH,
            difficulty=difficulty,
            zpd_zone=zone,
            max_minutes=max_minutes,
            is_safety_retracted=False,
        )
