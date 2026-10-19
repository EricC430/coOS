# Phase 1: Data Model Specification

**Feature**: M4.11 動態邊界任務池與 ZPD 盲盒管線 (Dynamic ZPD Gacha Pipeline)  
**Date**: 2026-10-19  
**Status**: Completed  

---

## 1. Relational Entities (SQLite Local Storage)

M4.11 遵循憲法 Principle I（L1 本地儲存原則），所有掌握度參數與任務紀錄均保存在本地 SQLite。

### 1.1 `role_skill_mastery`（BKT 技能掌握度狀態表）

記錄使用者在各角色、各細部技能範疇的多模態 BKT 參數，作為 ZONE 難度計算的硬性天花板。

```sql
CREATE TABLE IF NOT EXISTS role_skill_mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL,
    role_id VARCHAR(64) NOT NULL,
    skill_domain VARCHAR(64) NOT NULL,
    p_mastery REAL NOT NULL DEFAULT 0.30,          -- P(Lt) 掌握度機率 [0.0, 1.0]
    consecutive_successes INTEGER NOT NULL DEFAULT 0, -- 連續成功次數
    consecutive_failures INTEGER NOT NULL DEFAULT 0,  -- 連續失敗/放棄次數
    last_attempt_at TIMESTAMP NULL,                -- 最後挑戰時間
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_role_skill UNIQUE (user_id, role_id, skill_domain)
);

CREATE INDEX IF NOT EXISTS idx_role_skill_lookup 
ON role_skill_mastery (user_id, role_id);
```

### 1.2 `zpd_challenges`（動態挑戰任務實體表）

儲存由 LLM 或降級種子生成的挑戰實體與單一槽位流轉狀態。

```sql
CREATE TABLE IF NOT EXISTS zpd_challenges (
    id VARCHAR(64) PRIMARY KEY,                    -- UUID
    user_id VARCHAR(64) NOT NULL,
    role_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,                   -- 挑戰標題
    description TEXT NOT NULL,                     -- 詳細指引
    task_type VARCHAR(32) NOT NULL DEFAULT 'skill_stretch', -- 'skill_stretch' | 'restorative_serendipity'
    is_real_world BOOLEAN NOT NULL DEFAULT 0,      -- 是否為脫離螢幕實體行動
    difficulty VARCHAR(32) NOT NULL,               -- 'comfort' | 'just-manageable' | 'stretch' | 'restorative'
    skill_domain VARCHAR(64) NOT NULL,             -- 關聯技能領域
    estimated_minutes INTEGER NOT NULL DEFAULT 20, -- 預估時長 (15~45 min)
    xp_reward INTEGER NOT NULL DEFAULT 50,         -- 激勵 XP 額度 (30~100 XP)
    status VARCHAR(32) NOT NULL DEFAULT 'generated', -- 'generated' | 'accepted' | 'completed' | 'expired' | 'abandoned'
    zpd_zone VARCHAR(32) NOT NULL,                 -- 'core_zpd' | 'upper_stretch' | 'restorative_haven'
    scaffolding_hints TEXT NOT NULL DEFAULT '[]',  -- JSON Array: 2~3 條思考引導或除錯方向
    accepted_at TIMESTAMP NULL,                    -- 接受時間戳記
    completed_at TIMESTAMP NULL,                   -- 完成時間戳記
    expires_at TIMESTAMP NOT NULL,                 -- 軟性自然過期時間（24h 或次日 04:00 AM）
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zpd_active_slot 
ON zpd_challenges (user_id, role_id, status);
```

---

## 2. Pydantic Domain Schemas

### 2.1 核心資料物件定義 (`services/m4_11_zpd_pipeline/schemas.py`)

```python
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

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
    scaffolding_hints: List[str]
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

class CompleteChallengeRequest(BaseModel):
    challenge_id: str
    user_feeling: str = Field(min_length=1, description="真實感受（微摩擦反思）")
    user_action_plan: str = Field(min_length=1, description="下一步行動計畫")
    actual_minutes: Optional[int] = Field(default=None, ge=1)
```

---

## 3. State Machine & Lifecycle Transitions

### 3.1 挑戰狀態流轉表

| 當前狀態 | 觸發事件 | 下一狀態 | 系統行為 / 數據副作用 |
|---|---|---|---|
| *(None)* | `POST /draw_challenge` | `generated` | 由 LLM 或降級種子生成任務，回傳給前端預覽。若角色已有 `accepted` 任務，不自動覆蓋。 |
| `generated` | `POST /accept_challenge` | `accepted` | 寫入 `accepted_at`。若使用者選擇替換，舊的 `accepted` 任務自動轉為 `abandoned`。 |
| `generated` | 使用者忽略或再次重抽 | *(Discarded)* | 未被接受的 `generated` 任務在 1 小時後排程清理，不影響 BKT。 |
| `accepted` | `POST /complete_challenge` | `completed` | 檢核反思非空，呼叫 M6.5 `XPGatekeeper` 發放 XP；BKT 掌握度 $P(L_t)$ 獲得正向更新。 |
| `accepted` | 跨日結算或滿 24 小時 | `expired` | 自然過期，**0 XP 扣除**；BKT 掌握度進行輕微遺忘衰減。 |
| `accepted` | 使用者手動替換/放棄 | `abandoned` | **0 XP 扣除**；標記放棄原因，避免後續重複推薦相同題目。 |

---

## 4. GraphRAG (M5) Alignment Interface

依據 Q3 架構決策，資料實體預留與 M5 薩提爾深層認知圖譜對齊的擴充介面：
* 節點標籤：`(:SkillNode {domain: skill_domain, name: title})`
* 邊關係：`(:RoleContext)-[:PRACTICING {mastery: p_mastery}]->(:SkillNode)`
* 事件關係：`(:Reflection)-[:EVIDENCES_MASTERY {delta_p: +0.12}]->(:SkillNode)`
