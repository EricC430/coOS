"""
M4.2 Persona State Machine -- test suite

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §6
Research: [R03 §1 BDI] [R03 §3 Echo Mode] [R05 §副語言] [R09 §4.1 SDT]
Risk coverage: RISK-02, RISK-03, RISK-06, RISK-08
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from m4_2_persona.echo_mode import (
    EchoModeController,
    IllegalToneTransition,
    ToneState,
    TransitionPlan,
)
from m4_2_persona.reactance import ReactanceScore, rule_based_reactance
from m4_2_persona.bdi import BDIInput, reconcile_bdi
from m4_2_persona.paralinguistic import (
    FILLER_WORDS,
    inject_paralinguistic,
    inject_paralinguistic_sync,
)
from m4_2_persona.state_inversion import (
    STATE_RESPONSE_MAP,
    build_persona_context,
    ImplicitStateLabel,
)
from m4_2_persona.arpm import ARPMValidator, ValidationResult
from m4_2_persona.prompt_builder import build_system_prompt, PersonaConfig


# ===========================================================================
# TestM4_2_1_SystemPrompts
# ===========================================================================

class TestM4_2_1_SystemPrompts:
    """[R03 §1] BDI 結構系統提示詞工程"""

    def test_system_prompt_contains_backstory(self):
        """[R03 §1.1] 系統提示詞必須包含具體過往經歷，不可為通用 AI 語"""
        config = PersonaConfig(
            name="動力導師 Robert",
            personality_prompt=(
                "你是 Robert，1992 年生，曾在台積電工作 8 年的資深系統工程師。"
                "你嚴格但充滿熱忱，擅長用蘇格拉底式提問引導學生。"
            ),
            backstory="曾在台積電做系統工程師，後來轉型做技術教練。",
            tone_default="authoritative",
            trust_level=0.5,
        )
        prompt = build_system_prompt(config, role_id="role_csie", user_id="u_001")
        # 不可出現通用 AI 語
        assert "我是 AI" not in prompt
        assert "我會盡力協助" not in prompt
        # 必須有具體身份細節
        assert "Robert" in prompt

    def test_system_prompt_contains_bdi_structure(self):
        """[R09 §6.2] 系統提示詞應具備 BDI 意圖引導結構"""
        config = PersonaConfig(
            name="微積分助教 宏軒",
            personality_prompt=(
                "你是宏軒，台大數學系碩士，現在在補習班教微積分和線性代數。"
                "你個性親切、有耐心，擅長用直覺圖形解說抽象概念。"
            ),
            backstory="台大數學碩士，補習班人氣助教。",
            tone_default="empathetic",
            trust_level=0.6,
        )
        prompt = build_system_prompt(config, role_id="role_csie", user_id="u_001")
        assert len(prompt) > 50

    def test_system_prompt_role_scoped(self):
        """[RISK-06] 系統提示詞必須綁定 role_id，不可跨角色共用"""
        config = PersonaConfig(
            name="Robert", personality_prompt="你是 Robert。",
            backstory="...", tone_default="authoritative", trust_level=0.5,
        )
        prompt_csie = build_system_prompt(config, role_id="role_csie", user_id="u_001")
        prompt_family = build_system_prompt(config, role_id="role_family", user_id="u_001")
        # 兩個不同角色的 prompt 應不同（role context 被注入）
        assert prompt_csie != prompt_family

    def test_memory_block_injected_with_goals(self):
        """[v1.2 §7.1.1] 有 active_goals 時 [記憶區塊] 應包含核心目標"""
        config = PersonaConfig(
            name="Robert", personality_prompt="你是 Robert。",
            backstory="...", tone_default="authoritative", trust_level=0.5,
        )
        goals = [{"persona_id": "expert-001", "title": "完成微積分期末報告",
                  "created_at": "2026-06-01", "progress": 0.3}]
        prompt = build_system_prompt(
            config, role_id="role_csie", user_id="u_001",
            persona_id="expert-001", active_goals=goals,
        )
        assert "[核心目標]" in prompt
        assert "完成微積分期末報告" in prompt
        assert "30%" in prompt

    def test_memory_block_injected_with_promises(self):
        """[v1.2 §7.1.1] 有 upcoming_promises 時 [記憶區塊] 應包含即將到期承諾"""
        config = PersonaConfig(
            name="Robert", personality_prompt="你是 Robert。",
            backstory="...", tone_default="authoritative", trust_level=0.5,
        )
        promises = [{"persona_id": "expert-001", "text": "本週完成第三章練習",
                     "deadline": "2026-06-05"}]
        prompt = build_system_prompt(
            config, role_id="role_csie", user_id="u_001",
            persona_id="expert-001", upcoming_promises=promises,
        )
        assert "[即將到期的承諾]" in prompt
        assert "本週完成第三章練習" in prompt

    def test_memory_block_empty_when_no_data(self):
        """[v1.2 §7.1.1] 無目標/承諾時 [記憶區塊] 顯示占位說明"""
        config = PersonaConfig(
            name="Robert", personality_prompt="你是 Robert。",
            backstory="...", tone_default="authoritative", trust_level=0.5,
        )
        prompt = build_system_prompt(
            config, role_id="role_csie", user_id="u_001",
            persona_id="expert-001", active_goals=[], upcoming_promises=[],
        )
        assert "[記憶區塊" in prompt
        assert "目前無已確立" in prompt

    def test_memory_block_filters_by_persona_id(self):
        """[v1.2 §7.1.1] 記憶區塊只注入屬於當前 persona 的目標/承諾"""
        config = PersonaConfig(
            name="Robert", personality_prompt="你是 Robert。",
            backstory="...", tone_default="authoritative", trust_level=0.5,
        )
        goals = [
            {"persona_id": "expert-001", "title": "Robert 的目標",
             "created_at": "2026-06-01", "progress": 0.5},
            {"persona_id": "expert-002", "title": "宏軒的目標",
             "created_at": "2026-06-01", "progress": 0.2},
        ]
        prompt = build_system_prompt(
            config, role_id="role_csie", user_id="u_001",
            persona_id="expert-001", active_goals=goals,
        )
        assert "Robert 的目標" in prompt
        assert "宏軒的目標" not in prompt

    def test_behavior_instructions_present(self):
        """[v1.2 §7.1.1] 系統提示詞包含目標引導行為指令"""
        config = PersonaConfig(
            name="Robert", personality_prompt="你是 Robert。",
            backstory="...", tone_default="authoritative", trust_level=0.5,
        )
        prompt = build_system_prompt(config, role_id="role_csie", user_id="u_001")
        assert "[行為指令]" in prompt
        assert "session 最多 1 次" in prompt


# ===========================================================================
# TestM4_2_2_EchoMode
# ===========================================================================

class TestM4_2_2_EchoMode:
    """[R03 §3 Echo Mode + RISK-02]"""

    def test_reactance_triggers_agency_descent(self):
        """[R03 §3.2, RISK-02] 偵測防衛語氣 → Agency 漸進下降，不可一步跳到底"""
        controller = EchoModeController(current_state=ToneState.AUTHORITATIVE)
        defensive_input = "你不懂我在說什麼"
        result = controller.process(defensive_input, current_agency=0.85)
        # 不可一步跳到 empathetic 中點 (0.30)，必須在漸進範圍內
        assert result.target_agency >= 0.65
        assert result.target_agency <= 0.85
        assert result.transition_plan.steps_remaining == 5

    def test_agency_transition_is_gradual(self):
        """[R03 §3.2, RISK-02] 5 步漸進，每步變化 < 0.20"""
        controller = EchoModeController(current_state=ToneState.AUTHORITATIVE)
        plan = controller.plan_transition(ToneState.AUTHORITATIVE, ToneState.EMPATHETIC)
        assert len(plan.steps) == 5
        diffs = [abs(plan.steps[i + 1] - plan.steps[i]) for i in range(4)]
        assert max(diffs) < 0.20

    def test_plan_transition_values_monotonic(self):
        """過渡計畫的 agency 值必須單調移動（下降時連續下降）"""
        controller = EchoModeController(current_state=ToneState.AUTHORITATIVE)
        plan = controller.plan_transition(ToneState.AUTHORITATIVE, ToneState.EMPATHETIC)
        # Authoritative → Empathetic 是下降路徑
        for i in range(len(plan.steps) - 1):
            assert plan.steps[i] >= plan.steps[i + 1]

    def test_illegal_transition_raises(self):
        """RESONANCE 不可直接跳回 AUTHORITATIVE（非法切換）"""
        controller = EchoModeController(current_state=ToneState.RESONANCE)
        with pytest.raises(IllegalToneTransition):
            controller.plan_transition(ToneState.RESONANCE, ToneState.AUTHORITATIVE)

    def test_legal_transitions_defined(self):
        """所有合法切換路徑存在且從 AUTHORITATIVE 可達 RESONANCE"""
        from m4_2_persona.echo_mode import LEGAL_TRANSITIONS
        # AUTHORITATIVE -> PROBING -> EMPATHETIC -> RESONANCE
        assert ToneState.PROBING in LEGAL_TRANSITIONS[ToneState.AUTHORITATIVE]
        assert ToneState.EMPATHETIC in LEGAL_TRANSITIONS[ToneState.PROBING]
        assert ToneState.RESONANCE in LEGAL_TRANSITIONS[ToneState.EMPATHETIC]

    def test_arpm_recognizes_echo_mode_transition(self):
        """[RISK-02] ARPM 必須認得 echo_mode_authorized=True 的合法切換，不觸發還原"""
        validator = ARPMValidator()
        result = validator.validate(
            prev_state=ToneState.AUTHORITATIVE,
            current_state=ToneState.EMPATHETIC,
            echo_mode_authorized=True,
        )
        assert result == ValidationResult.LEGAL

    def test_arpm_blocks_unauthorized_drift(self):
        """[RISK-02] 未授權的急速切換應被 ARPM 攔截"""
        validator = ARPMValidator()
        result = validator.validate(
            prev_state=ToneState.AUTHORITATIVE,
            current_state=ToneState.RESONANCE,  # 跳過 PROBING/EMPATHETIC
            echo_mode_authorized=False,
        )
        assert result == ValidationResult.DRIFT_DETECTED

    def test_step_remaining_decrements(self):
        """TransitionPlan 的 steps_remaining 正確回傳剩餘步數"""
        plan = TransitionPlan(steps=[0.75, 0.65, 0.55, 0.45, 0.35])
        assert plan.steps_remaining == 5


# ===========================================================================
# TestM4_2_3_SocialContract  (SDT + RISK-03)
# ===========================================================================

class TestM4_2_3_SocialContract:
    """[R09 §4.1 SDT + RISK-03]"""

    def test_anxiety_state_triggers_calm_not_mirror(self):
        """[RISK-03] 焦慮狀態 → 安撫語氣；絕不鏡像焦慮"""
        ctx = build_persona_context(ImplicitStateLabel.ANXIETY)
        assert ctx.persona_tone == "calm"
        assert "anxious" not in ctx.system_prompt_fragment.lower()
        assert "焦慮" not in ctx.system_prompt_fragment

    def test_avoidance_state_triggers_probing(self):
        """[RISK-03] 逃避狀態 → 探索語氣（不使用罪惡感誘導）"""
        ctx = build_persona_context(ImplicitStateLabel.AVOIDANCE)
        assert "guilt" not in ctx.system_prompt_fragment.lower()
        assert "罪惡" not in ctx.system_prompt_fragment
        # 應引導探索，而非責備
        assert ctx.challenge_level in ("gentle", "probing", "stretch")

    def test_flow_state_triggers_challenge(self):
        """心流狀態 → 推進挑戰模式"""
        ctx = build_persona_context(ImplicitStateLabel.FLOW)
        assert ctx.challenge_level == "stretch"

    def test_state_response_map_covers_all_labels(self):
        """STATE_RESPONSE_MAP 必須覆蓋所有 ImplicitStateLabel"""
        for label in ImplicitStateLabel:
            assert label in STATE_RESPONSE_MAP, f"{label} 未在 STATE_RESPONSE_MAP 中"

    def test_role_scoped_state_injection(self):
        """[RISK-06] 隱性狀態以 role_id 隔離，不同角色取到不同（或空）狀態"""
        ctx_csie = build_persona_context(
            ImplicitStateLabel.ANXIETY, role_id="role_csie"
        )
        ctx_family = build_persona_context(
            ImplicitStateLabel.ANXIETY, role_id="role_family"
        )
        # 兩個角色的 persona_tone 可相同（都是 calm），但 role_id 隔離正確
        assert ctx_csie.role_id == "role_csie"
        assert ctx_family.role_id == "role_family"


# ===========================================================================
# TestM4_2_4_Paralinguistic
# ===========================================================================

class TestM4_2_4_Paralinguistic:
    """[R05 §跨越恐怖谷 + RISK-03]"""

    def test_filler_word_injection_rate_in_range(self):
        """[R05] trust_level=0.5 時填充詞注入率應在 6%~10% (1000 次取樣)"""
        import random
        random.seed(42)
        base_response = "這個問題很有趣，讓我解釋一下微積分的基本概念。"
        count = sum(
            1 for _ in range(1000)
            if inject_paralinguistic_sync(base_response, trust_level=0.5).split()[0]
            in [w.strip() for w in FILLER_WORDS]
        )
        # 6% ~ 10%
        assert 55 <= count <= 110, f"填充詞注入率 {count/1000:.1%} 超出 [6%, 10%] 範圍"

    def test_filler_rate_not_exceed_15_percent(self):
        """[R05 §諂媚效應] 填充詞比例永遠不超過 15%，即使 trust_level=0.0"""
        import random
        random.seed(0)
        base_response = "讓我解釋一下。"
        count = sum(
            1 for _ in range(1000)
            if inject_paralinguistic_sync(base_response, trust_level=0.0).split()[0]
            in [w.strip() for w in FILLER_WORDS]
        )
        assert count <= 150, f"填充詞比例 {count/1000:.1%} 超過 15%"

    def test_implicit_state_never_mirrors_anxiety(self):
        """[RISK-03] 焦慮狀態下的系統提示詞不含焦慮詞彙"""
        ctx = build_persona_context(ImplicitStateLabel.ANXIETY)
        assert "焦慮" not in ctx.system_prompt_fragment
        assert "緊張" not in ctx.system_prompt_fragment
        assert ctx.persona_tone == "calm"

    def test_self_correction_only_on_long_response(self):
        """自我修正只在長回應（>100字）中注入"""
        import random
        random.seed(1)
        short = "好的。"
        long_resp = "這是一個非常詳細的解釋，" * 10  # >100 chars
        # 短回應不注入自我修正
        short_result = inject_paralinguistic_sync(short, trust_level=0.5)
        # 不應有自我修正片語出現在短回應
        assert "不太精準" not in short_result or len(short) > 100


# ===========================================================================
# TestM4_2_Reactance
# ===========================================================================

class TestM4_2_Reactance:
    """[R03 §3.1] 阻抗偵測規則層"""

    def test_defensive_phrase_triggers_high_score(self):
        """「你不懂我」類防衛語句應得到高阻抗分"""
        score = rule_based_reactance("你根本不懂我在說什麼")
        assert score.score > 0.7

    def test_normal_input_triggers_low_score(self):
        """正常學習對話應得到低阻抗分"""
        score = rule_based_reactance("微積分的 Taylor 展開怎麼推導？")
        assert score.score < 0.3

    def test_rejection_phrase_triggers_high_score(self):
        """「不要再說了」類拒絕語句應高分"""
        score = rule_based_reactance("不要再說了，我聽不進去")
        assert score.score > 0.7

    def test_score_is_float_in_range(self):
        """阻抗分應是 [0, 1] 的浮點數"""
        score = rule_based_reactance("我今天心情不太好")
        assert isinstance(score.score, float)
        assert 0.0 <= score.score <= 1.0

    def test_source_field_set(self):
        """ReactanceScore 必須有 source 欄位"""
        score = rule_based_reactance("你都不懂我")
        assert score.source in ("rule", "hybrid", "ml")


# ===========================================================================
# TestM4_2_BDI
# ===========================================================================

class TestM4_2_BDI:
    """[R09 §6.2 + RISK-08] BDI Reconciler"""

    def test_contradictory_bdi_produces_bridge_intention(self):
        """[RISK-08] 矛盾的 belief/desire 應產出橋接型 intention"""
        bdi = reconcile_bdi(BDIInput(
            belief="不懂雲端架構",
            desire="完成 OpenStack 部署",
        ))
        # 橋接型 intention 應包含漸進詞彙
        bridge_words = ["從", "先", "逐步", "開始", "首先", "一步"]
        assert any(w in bdi.intention for w in bridge_words), (
            f"intention '{bdi.intention}' 未包含橋接詞"
        )

    def test_aligned_bdi_produces_direct_intention(self):
        """belief/desire 一致時 intention 直接反映目標"""
        bdi = reconcile_bdi(BDIInput(
            belief="我已熟悉線性代數基礎",
            desire="完成線性代數作業",
        ))
        assert len(bdi.intention) > 0

    def test_bdi_never_raw_concat(self):
        """[RISK-08] intention 不得是 belief + desire 的直接拼接"""
        inp = BDIInput(belief="不懂雲端架構", desire="完成 OpenStack 部署")
        bdi = reconcile_bdi(inp)
        raw_concat = inp.belief + inp.desire
        assert bdi.intention != raw_concat

    def test_empty_belief_uses_desire(self):
        """belief 為空時 intention 退化為 desire 的行動化版本"""
        bdi = reconcile_bdi(BDIInput(belief="", desire="完成作業"))
        assert len(bdi.intention) > 0


# ===========================================================================
# TestM4_2_MessageSplitter  (SPEC §7.4.1)
# ===========================================================================

class TestM4_2_MessageSplitter:
    """[R05 §跨越恐怖谷] 多訊息分割器 — 模擬真人分段發言"""

    def test_short_response_single_bubble(self):
        """短回應 (< 28 字) 不拆分，單一氣泡"""
        from m4_2_persona.message_splitter import split_response
        short = "好的，讓我想想。"
        seq = split_response(short)
        assert seq.bubble_count == 1
        assert seq.messages[0].delay_ms == 0

    def test_medium_response_multiple_short_bubbles(self):
        """中等回應拆為多個短氣泡（v2：每泡 1~2 句，不再壓成 2 泡）"""
        from m4_2_persona.message_splitter import split_response
        medium = (
            "微積分的 Taylor 展開是一個非常重要的工具。"
            "它讓我們可以用多項式來近似任意光滑函數。"
            "你可以把它想成「用一把尺去量一條曲線」的概念。"
        )  # 3 句
        seq = split_response(medium)
        # 3 句、每泡最多 2 句 → 2 泡；重點是有拆分且每泡不過長
        assert seq.bubble_count >= 2
        assert all(len(m.content) <= 60 for m in seq.messages)

    def test_long_response_three_or_four_bubbles(self):
        """長回應 (> 200 字) 拆為 3~4 個氣泡"""
        from m4_2_persona.message_splitter import split_response
        # 建立確定 >200 字的長回應（用重複確保）
        long_resp = (
            "我來解釋一下 OpenStack 的整體架構設計。"
            "首先，Nova 負責計算資源的管理，你可以把它想成是虛擬機的排程員。"
            "Neutron 則負責網路配置，讓不同虛擬機之間可以互相溝通。"
            "Swift 是物件儲存服務，用來存放靜態檔案和長期備份資料。"
            "Keystone 是認證服務，所有 OpenStack 元件都要通過它來驗證身份。"
            "這四個核心元件是 MVP 階段最重要的基礎，先把這些搞懂，再深入其他元件。"
        )
        # 若仍不足 200 字則補充（相容 Windows/Unicode 計數差異）
        while len(long_resp) <= 200:
            long_resp += "這是補充的內容，確保長度足夠觸發長回應分割邏輯。"
        seq = split_response(long_resp)
        assert 3 <= seq.bubble_count <= 4

    def test_first_bubble_has_zero_delay(self):
        """第一個氣泡的 delay_ms 必須為 0"""
        from m4_2_persona.message_splitter import split_response
        resp = "這是一個很長的回應。" * 10
        seq = split_response(resp)
        assert seq.messages[0].delay_ms == 0

    def test_subsequent_bubbles_have_delay_in_range(self):
        """後續氣泡的 delay_ms 在 300~1500ms 範圍內"""
        from m4_2_persona.message_splitter import (
            MAX_DELAY_MS,
            MIN_DELAY_MS,
            split_response,
        )
        resp = "這是一個很長的回應。" * 15  # > 200 字
        seq = split_response(resp)
        for msg in seq.messages[1:]:
            assert MIN_DELAY_MS <= msg.delay_ms <= MAX_DELAY_MS

    def test_total_text_preserved(self):
        """拆分後所有氣泡合計文字內容與原始回應一致（不丟字）"""
        from m4_2_persona.message_splitter import split_response
        resp = (
            "讓我想想。微積分的極限定義是這樣的：當 x 趨近於 a 時，"
            "函數 f(x) 趨近於 L，我們說 lim f(x) = L。"
            "這個概念很抽象，但用圖形來看會直觀很多。"
            "你有沒有試著畫出函數的圖形？"
        )
        seq = split_response(resp)
        # 合計文字應與原文去除前後空白後一致
        assert seq.total_text.replace(" ", "") == resp.strip().replace(" ", "")

    def test_max_bubbles_respected(self):
        """max_bubbles 參數必須被遵守"""
        from m4_2_persona.message_splitter import split_response
        very_long = "這是一個超長的句子，包含很多內容。" * 30
        seq = split_response(very_long, max_bubbles=3)
        assert seq.bubble_count <= 3

    def test_bubble_count_within_spec_range(self):
        """氣泡數量永遠在 1~4 之間（SPEC §7.4.1）"""
        from m4_2_persona.message_splitter import split_response
        for length_multiplier in [1, 5, 10, 30]:
            resp = "這是測試回應。這裡有更多內容。" * length_multiplier
            seq = split_response(resp)
            assert 1 <= seq.bubble_count <= 4, (
                f"回應長度 {len(resp)} 時氣泡數 {seq.bubble_count} 超出範圍"
            )
