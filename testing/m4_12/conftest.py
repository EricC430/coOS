import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICES_DIR = PROJECT_ROOT / "services"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from m4_12_hidden_achievement.models import (
    Base,
    HiddenAchievementModel,
    UserAchievementModel,
    EpistemicEvidenceQueueModel,
)


@pytest.fixture
def sqlite_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_achievements(db_session):
    achievements = [
        HiddenAchievementModel(
            id="ha_curious_cartographer_01",
            archetype="curiosity",
            name="本質探求者",
            description="主動追問底層原理達五層以上，跳脫既定提示指針。",
            flavor_text_template="「你所觸碰的不是表象，而是深邃的知識核心。」",
            rarity="rare",
            exp_reward=100,
            badge_icon_url="/assets/badges/cartographer.svg",
            eval_rules_json='{"regex_patterns": ["(底層|原理|IR|編譯器|SSA|AST|虛擬機器|記憶體佈局)", "(為什麼|如何實現|本質)"]}',
            is_hidden=True,
        ),
        HiddenAchievementModel(
            id="ha_reframe_alchemist_01",
            archetype="metacognition",
            name="心靈煉金術士",
            description="於反思中體察自我心理阻抗與脆弱，完成認知重構與接納。",
            flavor_text_template="「接納不完美的那一刻，真正的轉化已經開始。」",
            rarity="epic",
            exp_reward=150,
            badge_icon_url="/assets/badges/alchemist.svg",
            eval_rules_json='{"semantic_anchors": ["自省", "脆弱", "重構", "接納", "轉念"]}',
            is_hidden=True,
        ),
        HiddenAchievementModel(
            id="ha_serendipity_seeker_01",
            archetype="restoration",
            name="微光漫遊者",
            description="於高認知負荷之際，果斷走向真實世界完成注意力恢復實踐。",
            flavor_text_template="「微風與綠意撫平了焦慮，世界在此刻向你敞開。」",
            rarity="rare",
            exp_reward=80,
            badge_icon_url="/assets/badges/seeker.svg",
            eval_rules_json='{"semantic_anchors": ["散步", "烹飪", "探店", "脫離螢幕", "五感覺察"]}',
            is_hidden=True,
        ),
        HiddenAchievementModel(
            id="ha_polyglot_synthesizer_01",
            archetype="cross_synthesis",
            name="通識織網者",
            description="巧妙揉合兩種以上截然不同角色領域的概念，創造結構性突破。",
            flavor_text_template="「當邊界消融，跨界的火花照亮了未知的群島。」",
            rarity="legendary",
            exp_reward=250,
            badge_icon_url="/assets/badges/synthesizer.svg",
            eval_rules_json='{"semantic_anchors": ["跨領域", "知識融通", "類比遷移"]}',
            is_hidden=True,
        ),
    ]
    for ach in achievements:
        db_session.add(ach)
    db_session.commit()
    return achievements
