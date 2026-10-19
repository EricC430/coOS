from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ArchetypeEnum(str, Enum):
    CURIOSITY = "curiosity"
    METACOGNITION = "metacognition"
    RESTORATION = "restoration"
    CROSS_SYNTHESIS = "cross_synthesis"


class RarityEnum(str, Enum):
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class HiddenAchievementDTO(BaseModel):
    id: str
    archetype: ArchetypeEnum
    name: str
    description: str
    flavor_text_template: str
    rarity: RarityEnum
    exp_reward: int
    badge_icon_url: str
    eval_rules_json: str
    is_hidden: bool = True
    created_at: Optional[datetime] = None


class UnlockedAchievementItem(BaseModel):
    id: str
    archetype: ArchetypeEnum
    name: str
    description: str
    flavor_text: str
    rarity: RarityEnum
    exp_reward: int
    badge_icon_url: str
    origin_role_id: Optional[str] = None
    unlocked_at: datetime
    is_new: bool = False
    context_summary: Optional[str] = None


class AchievementWallResponse(BaseModel):
    user_id: str
    total_unlocked_count: int
    total_visible_count: Optional[int] = None
    items: List[UnlockedAchievementItem] = Field(default_factory=list)


class UnlockEventPayload(BaseModel):
    event_type: str = "HIDDEN_ACHIEVEMENT_UNLOCKED"
    achievement_id: str
    archetype: ArchetypeEnum
    name: str
    description: str
    flavor_text: str
    rarity: RarityEnum
    exp_reward: int
    badge_icon_url: str
    origin_role_id: Optional[str] = None
    unlocked_at: datetime
    context_summary: Optional[str] = None


class AckAchievementRequest(BaseModel):
    user_id: str
    achievement_ids: List[str]


class AckAchievementResponse(BaseModel):
    success: bool
    acknowledged_count: int


class QueueStatusResponse(BaseModel):
    pending_count: int
    processing_count: int
    failed_count: int
