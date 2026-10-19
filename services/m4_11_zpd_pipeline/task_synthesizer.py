import json
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schemas import ChallengeStatus, TaskDifficulty, TaskType

logger = logging.getLogger(__name__)

SEEDS_PATH = Path(__file__).resolve().parent / "seeds.json"


def calculate_soft_expiration(now: Optional[datetime] = None) -> datetime:
    """
    Calculate soft expiration: 24 hours from current time, or aligned to 04:00 AM next day.
    Defaulting to now + 24 hours in UTC.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return now + timedelta(hours=24)


class TaskSynthesizer:
    def __init__(self, seeds_file: Optional[Path] = None):
        self.seeds_path = seeds_file or SEEDS_PATH
        self._seeds: List[Dict[str, Any]] = []
        self._load_seeds()

    def _load_seeds(self) -> None:
        if not self.seeds_path.exists():
            logger.warning("seeds.json not found at %s, using empty fallback list", self.seeds_path)
            self._seeds = []
            return
        try:
            with open(self.seeds_path, "r", encoding="utf-8") as f:
                self._seeds = json.load(f)
        except Exception as e:
            logger.error("Failed to load seeds from %s: %s", self.seeds_path, e)
            self._seeds = []

    def synthesize_fallback(
        self,
        user_id: str,
        role_id: str,
        preferred_task_type: Optional[TaskType] = None,
        preferred_difficulty: Optional[TaskDifficulty] = None,
        context_vars: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fast (<300ms) dual-tier offline fallback that samples from seeds and performs slot-filling.
        """
        candidates = self._seeds
        if preferred_task_type:
            filtered = [s for s in candidates if s.get("task_type") == preferred_task_type.value]
            if filtered:
                candidates = filtered

        if preferred_difficulty:
            filtered = [s for s in candidates if s.get("difficulty") == preferred_difficulty.value]
            if filtered:
                candidates = filtered

        if not candidates:
            # Absolute hardcoded safety fallback if seeds.json is empty
            seed = {
                "title": "梳理今日程式碼並手寫 3 點收穫",
                "description": "回顧今日所撰寫的程式碼，在紙上或數位筆記寫下 3 點關鍵洞察與 1 個改善方向。",
                "task_type": "skill_stretch",
                "is_real_world": False,
                "difficulty": "comfort",
                "skill_domain": "general",
                "estimated_minutes": 15,
                "xp_reward": 35,
                "zpd_zone": "core_zpd",
                "scaffolding_hints": ["回顧最近一個 Git commit", "記錄卡關最久的地方是如何被解決的"],
            }
        else:
            seed = random.choice(candidates)

        now = datetime.now(timezone.utc)
        challenge_id = f"zpd_{uuid.uuid4().hex[:12]}"
        title = seed.get("title", "自訂延伸挑戰")
        desc = seed.get("description", "")
        hints = list(seed.get("scaffolding_hints", []))

        # Slot-filling with context variables if available
        if context_vars:
            topic = context_vars.get("interest_topic")
            friction = context_vars.get("friction_point")
            if topic:
                title = f"[{topic}] {title}"
            if friction:
                hints.append(f"針對痛點提示：嘗試回顧 {friction} 的相關概念")

        task_type_str = seed.get("task_type", TaskType.SKILL_STRETCH.value)
        is_restorative = task_type_str == TaskType.RESTORATIVE_SERENDIPITY.value or bool(seed.get("is_real_world", False))

        is_real_world = True if is_restorative else bool(seed.get("is_real_world", False))
        est_min = min(20, int(seed.get("estimated_minutes", 15))) if is_restorative else int(seed.get("estimated_minutes", 20))
        diff = TaskDifficulty.RESTORATIVE.value if is_restorative else seed.get("difficulty", TaskDifficulty.JUST_MANAGEABLE.value)
        zone = "restorative_haven" if is_restorative else seed.get("zpd_zone", "core_zpd")

        return {
            "id": challenge_id,
            "user_id": user_id,
            "role_id": role_id,
            "title": title,
            "description": desc,
            "task_type": TaskType.RESTORATIVE_SERENDIPITY.value if is_restorative else TaskType.SKILL_STRETCH.value,
            "is_real_world": is_real_world,
            "difficulty": diff,
            "skill_domain": seed.get("skill_domain", "restoration" if is_restorative else "general"),
            "estimated_minutes": est_min,
            "xp_reward": int(seed.get("xp_reward", 45)),
            "status": ChallengeStatus.GENERATED.value,
            "zpd_zone": zone,
            "scaffolding_hints": hints,
            "expires_at": calculate_soft_expiration(now),
            "created_at": now,
        }
