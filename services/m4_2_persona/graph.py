"""
M4.2 -- LangGraph Persona 狀態機節點圖

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.1
Research: [R03 §1] BDI 節點結構  [R03 §3] Echo Mode 節點
          [R05] 副語言注入節點    [R09 §6.2] BDI Reconciler 節點
Risk: RISK-02, RISK-03, RISK-06, RISK-08
"""
from __future__ import annotations

import logging
import os
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .arpm import ARPMValidator, ValidationResult
from .bdi import BDIInput, reconcile_bdi
from .echo_mode import EchoModeController, ToneState
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
    bdi_belief: str
    bdi_desire: str
    bdi_intention: str | None
    current_tone: str           # ToneState 值
    current_agency: float
    raw_response: str | None    # LLM 生成的裸回應
    final_response: str | None  # 注入副語言後的最終回應
    arpm_blocked: bool


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
    注入 BDI intention + 隱性狀態 + 系統提示詞後生成。
    """
    config_dict = state.get("persona_config") or {}
    config = PersonaConfig(
        name=config_dict.get("name", "AI 幫手"),
        personality_prompt=config_dict.get("personality_prompt", "你是一個有幫助的 AI 助手。"),
        backstory=config_dict.get("backstory", ""),
        tone_default=config_dict.get("tone_default", "authoritative"),
        trust_level=config_dict.get("trust_level", 0.5),
    )

    role_id = state.get("role_id", "default")
    user_id = state.get("user_id", "")
    system_prompt = build_system_prompt(config, role_id=role_id, user_id=user_id)

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
    response = await _call_gemini(system_prompt, user_message, config.tone_default)

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


async def arpm_audit_node(state: PersonaState) -> PersonaState:
    """
    [R03 §2] ARPM 監督節點：記錄狀態切換事件。
    完整 ARPM 由 M4.9 實作，此處僅記錄 raw_tracking_logs。
    """
    if state.get("arpm_blocked"):
        logger.info("[M4.2] ARPM audit: transition blocked, logged.")
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
              → echo_mode → persona_responder → paralinguistic → arpm_audit
    """
    graph = StateGraph(PersonaState)

    graph.add_node("drift_filter", drift_input_filter_node)
    graph.add_node("bdi_reconciler", bdi_reconciler_node)
    graph.add_node("reactance_detector", reactance_detector_node)
    graph.add_node("echo_mode", echo_mode_node)
    graph.add_node("persona_responder", persona_responder_node)
    graph.add_node("paralinguistic", paralinguistic_node)
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
    graph.add_edge("paralinguistic", "arpm_audit")
    graph.add_edge("arpm_audit", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# LLM 呼叫 (與 M4.1 共用 Gemini client)
# ---------------------------------------------------------------------------

async def _call_gemini(system_prompt: str, user_message: str, tone: str) -> str | None:
    """呼叫 Gemini API 生成 Persona 回應，使用 M4.1 共用的 client。"""
    try:
        from m4_1_router.routing_engine import get_cloud_llm_client
        client = get_cloud_llm_client("gemini-2.0-flash")
        
        full_prompt = (
            f"SYSTEM:\n{system_prompt}\n\n"
            f"USER:\n{user_message}\n\n"
            f"ASSISTANT (以 {tone} 語氣回應，繁體中文):"
        )
        # 覆蓋預設的 maxOutputTokens 以允許長回應
        async def complete_with_more_tokens(prompt: str) -> str:
            import os
            from config import get_settings
            import httpx
            settings = get_settings()
            api_key = settings.gemini_api_key or os.environ.get("GOOGLE_API_KEY")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
            }
            async with httpx.AsyncClient(timeout=15.0) as http_client:
                resp = await http_client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

        return await complete_with_more_tokens(full_prompt)
    except Exception as e:
        logger.warning("[M4.2] _call_gemini failed: %s", e)
        return None


_compiled_graph = None


def get_persona_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_persona_graph()
    return _compiled_graph
