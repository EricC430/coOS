"""
M4.2 -- LangGraph Persona 狀態機節點圖

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.1
Research: [R03 §1] BDI 節點結構  [R03 §3] Echo Mode 節點
          [R05] 副語言注入節點    [R09 §6.2] BDI Reconciler 節點
Risk: RISK-02, RISK-03, RISK-06, RISK-08
"""
from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .arpm import ARPMValidator, ValidationResult
from .bdi import BDIInput, reconcile_bdi
from .echo_mode import EchoModeController, ToneState
from .message_splitter import split_response  # [GAP-B2] 多訊息分割器
from .paralinguistic import inject_paralinguistic
from .prompt_builder import PersonaConfig, build_system_prompt
from .reactance import detect_reactance
from .state_inversion import ImplicitStateLabel, build_persona_context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph 狀態
# ---------------------------------------------------------------------------

class PersonaState(TypedDict, total=False):
    thread_id: str
    role_id: str
    user_id: str
    user_message: str
    persona_id: str
    persona_config: dict        # PersonaConfig 序列化
    implicit_state: str | None  # M4.8 輸入（ImplicitStateLabel）
    chat_history: list | None   # 近期對話紀錄，供 persona 保持連貫
    bdi_belief: str
    bdi_desire: str
    bdi_intention: str | None
    current_tone: str           # ToneState 值
    current_agency: float
    raw_response: str | None    # LLM 生成的裸回應
    final_response: str | None  # 注入副語言後的最終回應
    split_messages: list | None  # [GAP-B2] message_splitter 拆分後的多氣泡序列
    arpm_blocked: bool
    active_goals: list | None       # [R03 §3] 角色目標，由 M4.1 傳入，注入記憶區塊
    upcoming_promises: list | None  # [R03 §3] 角色承諾，由 M4.1 傳入，注入記憶區塊


# ---------------------------------------------------------------------------
# 節點實作
# ---------------------------------------------------------------------------

async def drift_input_filter_node(state: PersonaState) -> PersonaState:
    """
    [R02 §DRIFT] 第一道安全閘：驗證輸入不含 Prompt Injection。
    M4.1.4 DRIFT 已在 Router 層做第一道，此處為 Persona 層的二次確認。
    """
    from m4_1_router.drift import drift_validate
    result = drift_validate(state.get("user_message", ""))
    if result.blocked:
        logger.warning("[M4.2] DRIFT blocked in Persona layer: %s", result.reason)
        return {**state, "final_response": "（系統安全過濾）", "arpm_blocked": True}
    return state


async def bdi_reconciler_node(state: PersonaState) -> PersonaState:
    """
    [R09 §6.2] BDI Reconciler：belief + desire → intention。
    [RISK-08] 禁止直接拼接，必須橋接。
    """
    inp = BDIInput(
        belief=state.get("bdi_belief", ""),
        desire=state.get("bdi_desire", ""),
    )
    output = reconcile_bdi(inp)
    return {**state, "bdi_intention": output.intention}


async def reactance_detector_node(state: PersonaState) -> PersonaState:
    """
    [R03 §3.1] 阻抗偵測：規則層 + ML 層混合。
    結果存入 state 供 echo_mode_node 使用。
    """
    score = await detect_reactance(state.get("user_message", ""))
    return {**state, "_reactance_score": score.score, "_reactance_source": score.source}


async def echo_mode_node(state: PersonaState) -> PersonaState:
    """
    [R03 §3.2] Echo Mode 漸進切換。
    [RISK-02] 切換計畫存入 state，供 ARPM 驗證。
    """
    current_tone = ToneState(state.get("current_tone", ToneState.AUTHORITATIVE))
    current_agency = state.get("current_agency", 0.85)
    user_msg = state.get("user_message", "")

    controller = EchoModeController(current_state=current_tone)
    result = controller.process(user_msg, current_agency=current_agency)

    # ARPM 驗證
    validator = ARPMValidator()
    target_tone = controller._next_lower_state(current_tone) if result.triggered else current_tone
    arpm_result = validator.validate(
        prev_state=current_tone,
        current_state=target_tone,
        echo_mode_authorized=result.triggered,
    )

    if arpm_result == ValidationResult.DRIFT_DETECTED:
        logger.warning("[M4.2] ARPM blocked Echo Mode transition: %s → %s", current_tone, target_tone)
        return {**state, "arpm_blocked": True, "current_agency": current_agency}

    return {
        **state,
        "current_tone": target_tone.value,
        "current_agency": result.target_agency,
        "arpm_blocked": False,
    }


async def persona_responder_node(state: PersonaState) -> PersonaState:
    """
    M4.2 主回應節點：呼叫雲端 LLM 生成 Persona 回應。
    [W3] PersonaCard v2 編譯 → 取代原始 personality_prompt。
    [W4] MI 選擇器注入行為策略指令。
    注入 BDI intention + 隱性狀態 + 系統提示詞後生成。
    """
    config_dict = state.get("persona_config") or {}

    # [W3] 嘗試從 persona_card JSON 編譯結構化提示詞
    compiled_prompt = None
    anti_sycophancy_stances = None
    card_data: dict | None = None
    raw_card_str = config_dict.get("persona_card")
    if raw_card_str:
        try:
            import json
            card_data = json.loads(raw_card_str) if isinstance(raw_card_str, str) else raw_card_str
            from .persona_card import persona_card_from_dict, compile_to_prompt
            card = persona_card_from_dict(card_data)
            compiled_prompt = compile_to_prompt(card)
            anti_sycophancy_stances = card_data.get("stances")
            logger.info("[M4.2] PersonaCard v2 compiled for %s", config_dict.get("name", "?"))
        except Exception as e:
            logger.warning("[M4.2] PersonaCard compile fallback: %s", e)
            card_data = None

    config = PersonaConfig(
        name=config_dict.get("name", "AI 幫手"),
        personality_prompt=compiled_prompt or config_dict.get("personality_prompt", "你是一個有幫助的 AI 助手。"),
        backstory=config_dict.get("backstory", ""),
        tone_default=config_dict.get("tone_default", "authoritative"),
        trust_level=config_dict.get("trust_level", 0.5),
        persona_card=card_data,  # [R05] 供 prompt_builder 注入中文說話風格與跳過散文截斷
    )

    role_id = state.get("role_id", "default")
    user_id = state.get("user_id", "")
    persona_id = state.get("persona_id", "")

    # [W4] MI 選擇器：根據阻抗/隱性狀態/使用者訊息選擇 MI 行為策略
    mi_directive_str = None
    try:
        from .mi_selector import select_mi_technique
        reactance_score = state.get("_reactance_score", 0.0)
        implicit_state = state.get("implicit_state")
        user_message = state.get("user_message", "")
        mi_result = select_mi_technique(
            reactance_score=reactance_score,
            implicit_state=implicit_state,
            tone_state=state.get("current_tone", "authoritative"),
            user_message=user_message,
        )
        mi_directive_str = mi_result.instruction
        if mi_result.forbidden_actions:
            mi_directive_str += "\n禁止：" + "、".join(mi_result.forbidden_actions)
    except Exception as e:
        logger.warning("[M4.2] MI selector failed: %s", e)

    system_prompt = build_system_prompt(
        config,
        role_id=role_id,
        user_id=user_id,
        persona_id=persona_id,
        active_goals=state.get("active_goals") or [],
        upcoming_promises=state.get("upcoming_promises") or [],
        mi_directive=mi_directive_str,
        anti_sycophancy_stances=anti_sycophancy_stances,
    )

    # 注入隱性狀態情境 (REMT)
    implicit_label_str = state.get("implicit_state")
    if implicit_label_str:
        try:
            label = ImplicitStateLabel(implicit_label_str)
            ctx = build_persona_context(label, role_id=role_id, user_id=user_id)
            system_prompt += f"\n\n【當前情境調整】\n{ctx.system_prompt_fragment}"
        except ValueError:
            pass

    # 注入 BDI intention
    intention = state.get("bdi_intention")
    if intention:
        system_prompt += f"\n\n【使用者行動意圖】{intention}"

    # 呼叫 Gemini API
    user_message = state.get("user_message", "")
    chat_history = state.get("chat_history") or []
    response = await _call_gemini(system_prompt, user_message, config.tone_default, chat_history)

    return {**state, "raw_response": response}


async def paralinguistic_node(state: PersonaState) -> PersonaState:
    """
    [R05 §跨越恐怖谷] 副語言瑕疵注入。
    降級：若 raw_response 為 None（LLM 超時）直接跳過。
    """
    raw = state.get("raw_response")
    if not raw:
        return {**state, "final_response": "（系統暫時無法回應，請稍後再試）"}

    trust_level = (state.get("persona_config") or {}).get("trust_level", 0.5)
    final = await inject_paralinguistic(raw, trust_level=trust_level)
    return {**state, "final_response": final}


async def message_splitter_node(state: PersonaState) -> PersonaState:
    """
    [GAP-B2 修復][R05 §跨越恐怖谷] 多訊息分割器節點。
    [R05] 模擬真人分段發言，拆為 1~4 個氣泡（依回應長度分級）。
    skip 條件：final_response 為 None（已被上游阻斷）。
    """
    final = state.get("final_response")
    if not final:
        return {**state, "split_messages": []}

    seq = split_response(final)
    # 序列化為可 JSON 的 list[dict]
    bubbles = [
        {"content": msg.content, "delay_ms": msg.delay_ms}
        for msg in seq.messages
    ]
    return {**state, "split_messages": bubbles}


async def arpm_audit_node(state: PersonaState) -> PersonaState:
    """
    [R03 §2] ARPM 監督節點：記錄狀態切換事件。
    [W5] ARPM-lite Claim Ledger：背景抽取 persona 事實宣稱，偵測矛盾。
    完整 ARPM 由 M4.9 實作，此處僅記錄 raw_tracking_logs。
    """
    if state.get("arpm_blocked"):
        logger.info("[M4.2] ARPM audit: transition blocked, logged.")

    # [W5] Claim Ledger: 非阻塞式背景抽取
    final_response = state.get("final_response")
    if final_response:
        try:
            from .claim_ledger import ClaimLedger
            # Per-persona ledger (MVP: in-memory, per-invocation; future: persist per persona_id)
            ledger = ClaimLedger()
            claims = ledger.extract_claims(final_response)
            if claims:
                drift_events = ledger.check_contradictions()
                if drift_events:
                    logger.warning(
                        "[M4.2] ARPM-lite drift detected: %d contradictions in %s",
                        len(drift_events), state.get("persona_id", "?"),
                    )
                    # Emit to raw_tracking_logs (non-blocking)
                    try:
                        from m0_4_logging.writer import get_logger as get_log_writer
                        log_writer = get_log_writer()
                        import json
                        await log_writer.emit(
                            module="M4.2",
                            action="persona_drift_detected",
                            level="WARNING",
                            payload=json.dumps({
                                "persona_id": state.get("persona_id", ""),
                                "drift_count": len(drift_events),
                                "claims_count": len(claims),
                                "sample_contradiction": drift_events[0].contradiction_reason if drift_events else "",
                            }, ensure_ascii=False),
                            role_id=state.get("role_id", ""),
                        )
                    except Exception as log_err:
                        logger.debug("[M4.2] Failed to emit drift log: %s", log_err)
        except Exception as e:
            logger.debug("[M4.2] Claim ledger extraction failed: %s", e)

    return state


# ---------------------------------------------------------------------------
# 條件分支
# ---------------------------------------------------------------------------

def should_abort(state: PersonaState) -> str:
    """DRIFT 或 ARPM 阻擋時提前結束。"""
    if state.get("arpm_blocked") and state.get("final_response"):
        return "abort"
    return "continue"


# ---------------------------------------------------------------------------
# 圖構建
# ---------------------------------------------------------------------------

def build_persona_graph() -> StateGraph:
    """
    [R03 §1] 建構 M4.2 Persona 狀態機 LangGraph 圖。
    節點順序：drift_filter → bdi_reconciler → reactance_detector
              → echo_mode → persona_responder → paralinguistic
              → message_splitter → arpm_audit

    [GAP-B2] message_splitter 已接入 paralinguistic 之後，解決多氣泡缺失問題。
    """
    graph = StateGraph(PersonaState)

    graph.add_node("drift_filter", drift_input_filter_node)
    graph.add_node("bdi_reconciler", bdi_reconciler_node)
    graph.add_node("reactance_detector", reactance_detector_node)
    graph.add_node("echo_mode", echo_mode_node)
    graph.add_node("persona_responder", persona_responder_node)
    graph.add_node("paralinguistic", paralinguistic_node)
    graph.add_node("message_splitter", message_splitter_node)  # [GAP-B2]
    graph.add_node("arpm_audit", arpm_audit_node)

    graph.set_entry_point("drift_filter")
    graph.add_conditional_edges("drift_filter", should_abort, {
        "abort": END,
        "continue": "bdi_reconciler",
    })
    graph.add_edge("bdi_reconciler", "reactance_detector")
    graph.add_edge("reactance_detector", "echo_mode")
    graph.add_conditional_edges("echo_mode", should_abort, {
        "abort": "arpm_audit",
        "continue": "persona_responder",
    })
    graph.add_edge("persona_responder", "paralinguistic")
    graph.add_edge("paralinguistic", "message_splitter")  # [GAP-B2]
    graph.add_edge("message_splitter", "arpm_audit")      # [GAP-B2]
    graph.add_edge("arpm_audit", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# LLM 呼叫 (與 M4.1 共用 Gemini client)
# ---------------------------------------------------------------------------

async def _call_gemini(
    system_prompt: str,
    user_message: str,
    tone: str,
    chat_history: list[dict] | None = None,
) -> str | None:
    """呼叫 Gemini API 生成 Persona 回應。使用 M4.1 共用 client（含 rate limiting + backoff）。"""
    from m4_1_router.routing_engine import (
        PERSONA_MODEL,
        PERSONA_MODEL_FALLBACK,
        RateLimitError,
        ServiceUnavailableError,
        get_cloud_llm_client,
    )

    # 組裝近期對話歷史（最多 8 輪 = 16 條）
    history_block = ""
    if chat_history:
        recent = chat_history[-16:]
        lines = []
        for h in recent:
            role_label = "使用者" if h.get("role") == "user" else "你"
            lines.append(f"{role_label}：{h.get('content', '')}")
        history_block = "\n【近期對話】\n" + "\n".join(lines) + "\n"

    # [R05 §治療同盟][R03 §4.2 State Inversion] 真人聊天節奏 + 共情骨架
    output_rules = (
        "\n【回應格式規則 — 像真人傳訊息，不要像 AI 助理】\n"
        "- 繁體中文，口語自然。預設很短：一次最多 3 句，每句都短。\n"
        "- 一則回覆只問「一個」問題；禁止把多個問題塞進同一則回覆。\n"
        "- 初次見面只簡短自我介紹一句 + 一個輕鬆的問題，不要一次交代完整學經歷背景"
        "（背景在後續對話自然帶出即可）。\n"
        "- [R03 §4.2] 若使用者焦慮、卡關或挫折：先共情安撫，再回應。"
        "嚴禁催促語氣（如「既然你…就直接…」「別浪費時間」「我們就直接切入」）。\n"
        "- 不譴責使用者（例如稱呼、用詞），那類小事不必在回覆中糾正。\n"
        "- 形容詞節制，不要堆砌華麗詞藻；像朋友講話那樣。\n"
        "- 禁止使用條列式。禁止每次都用問句結尾——連續問過就改用陳述句或給具體一小步建議。\n"
        "- 只有在情緒濃厚或需要解釋複雜概念時，才允許稍長（最多 5~20 句）。\n"
        "- 保持你的個人語氣和過往經歷，不要說「我是AI」。\n"
    )

    full_prompt = (
        f"SYSTEM:\n{system_prompt}{output_rules}"
        f"{history_block}\n"
        f"使用者：{user_message}\n\n"
        f"你（以 {tone} 語氣，繁體中文）："
    )

    for model in (PERSONA_MODEL, PERSONA_MODEL_FALLBACK):
        try:
            client = get_cloud_llm_client(model)
            return await client.complete(full_prompt, max_output_tokens=400, temperature=0.75)
        except (RateLimitError, ServiceUnavailableError) as e:
            logger.warning("[M4.2] _call_gemini %s failed: %s, trying fallback", model, e)
        except Exception as e:
            logger.warning("[M4.2] _call_gemini unexpected error: %s", e)
            return None

    logger.error("[M4.2] _call_gemini: all models exhausted")
    return None


_compiled_graph = None


def get_persona_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_persona_graph()
    return _compiled_graph
