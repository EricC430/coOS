from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskType(str, Enum):
    SKILL_STRETCH = "skill_stretch"
    RESTORATIVE_SERENDIPITY = "restorative_serendipity"


class TaskDifficulty(str, Enum):
    COMFORT = "comfort"
    JUST_MANAGEABLE = "just-manageable"
    STRETCH = "stretch"
    RESTORATIVE = "restorative"


class ChallengeStatus(str, Enum):
    GENERATED = "generated"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ABANDONED = "abandoned"


class ZPDChallengeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role_id: str
    title: str
    description: str
    task_type: TaskType
    is_real_world: bool
    difficulty: TaskDifficulty
    skill_domain: str
    estimated_minutes: int = Field(ge=10, le=60)
    xp_reward: int = Field(ge=10, le=200)
    status: ChallengeStatus
    zpd_zone: str
    scaffolding_hints: List[str] = Field(default_factory=list)
    accepted_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime


class DrawChallengeRequest(BaseModel):
    user_id: str = "default_user"
    role_id: str
    force_fallback: bool = False


class AcceptChallengeRequest(BaseModel):
    challenge_id: str
    replace_existing: bool = True
    role_id: Optional[str] = None


class CompleteChallengeRequest(BaseModel):
    challenge_id: str
    user_feeling: str = Field(min_length=1, description="真實感受（微摩擦反思）")
    user_action_plan: str = Field(min_length=1, description="下一步行動計畫")
    actual_minutes: Optional[int] = Field(default=None, ge=1)
    role_id: Optional[str] = None


class ActiveChallengeResponse(BaseModel):
    active_challenge: Optional[ZPDChallengeDTO] = None


class AcceptChallengeResponse(BaseModel):
    success: bool
    active_challenge: ZPDChallengeDTO


class CompleteChallengeResponse(BaseModel):
    success: bool
    awarded_xp: int
    transaction_id: str
    new_p_mastery: float
