"""
M4.1 -- LangGraph 頂層協調圖

SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.1
Research: [R09: MAS §6.1] 多智能體頂層協調圖 (含安全過濾與信心分流)
         [R03 §1] Persona Agent 容器的 LangGraph 節點結構
"""
from __future__ import annotations

import asyncio
import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from m4_2_persona.graph import get_persona_graph

from .drift import drift_validate
from .routing_engine import route_with_confidence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 工具型 AI 緊急 fallback 模板（Gemini 完全不可用時使用）
# ---------------------------------------------------------------------------
_TOOL_FALLBACK_RESPONSES = [
    "了解！你說的這個方向很值得深聊，能多說一點你目前的狀況嗎？",
    "好的，我聽到了。你現在最卡住的地方是什麼？",
    "有意思，我們來拆解一下——你目前進展到哪個階段了？",
    "收到！先跟我說說你的背景，這樣我能給你更精準的建議。",
]
_fallback_idx = 0


def _tool_ai_fallback(user_msg: str) -> str:  # noqa: ARG001
    global _fallback_idx
    resp = _TOOL_FALLBACK_RESPONSES[_fallback_idx % len(_TOOL_FALLBACK_RESPONSES)]
    _fallback_idx += 1
    return resp


async def _tool_ai_reply_gemini(
    user_msg: str,
    active_experts: list,
    history: list[dict] | None = None,
) -> tuple[str, bool]:
    """
    工具型 AI 以 Gemini 生成真實對話（帶歷史），並偵測是否建議配對專家。
    返回 (reply_text, suggest_match)。
    """
    from .routing_engine import (
        PERSONA_MODEL,
        PERSONA_MODEL_FALLBACK,
        RateLimitError,
        ServiceUnavailableError,
        get_cloud_llm_client,
    )

    expert_domains = []
    for e in active_experts:
        name = e.get("name", "")
        domain = e.get("domain", "")
        if name:
            expert_domains.append(f"{name}（{domain}）" if domain else name)
    expert_list_str = "、".join(expert_domains) if expert_domains else "暫無"

    # 建立對話歷史片段（最近 6 輪）
    history_block = ""
    if history:
        recent = history[-12:]  # 最多 6 輪 (user+assistant pairs)
        lines = []
        for h in recent:
            role_label = "使用者" if h.get("role") == "user" else "助理"
            lines.append(f"{role_label}：{h.get('content', '')}")
        history_block = "\n".join(lines)

    system_prompt = (
        "你是 coOS 系統的工具型助理 AI，你的任務是透過對話幫使用者釐清他的目標與方向。\n"
        "風格要求：口語、簡短（1~2句）、不說廢話、不用條列式、像真人朋友聊天。\n"
        "絕對禁止：不要說「都可以」、「隨時」、「歡迎」這類廢話結尾。\n"
        "每次只問一個具體問題，推動對話往更具體的方向走。\n\n"
        "【配對判斷規則】\n"
        f"系統目前有這些專家可以配對：{expert_list_str}\n"
        "當你判斷使用者的需求已經足夠具體（例如：已知道要找哪方面工作、有明確學習目標、"
        "有具體專案要做），請在回應的最後單獨一行輸出 [SUGGEST_MATCH]。\n"
        "若使用者還在摸索方向，繼續對話引導，不要輸出這個標記。"
    )

    # 組合 prompt（帶歷史）
    history_section = f"\n【對話紀錄】\n{history_block}\n" if history_block else ""
    full_prompt = (
        f"SYSTEM:\n{system_prompt}"
        f"{history_section}\n"
        f"使用者：{user_msg}\n"
        f"助理（繁體中文，1~2句，口語）："
    )

    last_err: Exception | None = None
    for model in (PERSONA_MODEL, PERSONA_MODEL_FALLBACK):
        try:
            client = get_cloud_llm_client(model)
            raw = await client.complete(full_prompt, max_output_tokens=150, temperature=0.7)
            suggest_match = "[SUGGEST_MATCH]" in raw
            reply = raw.replace("[SUGGEST_MATCH]", "").strip()
            return reply, suggest_match
        except (RateLimitError, ServiceUnavailableError) as e:
            logger.warning("[M4.1] tool_ai_gemini %s failed: %s", model, e)
            last_err = e
        except Exception as e:
            logger.warning("[M4.1] tool_ai_gemini unexpected: %s", e)
            last_err = e

    logger.warning("[M4.1] tool_ai_gemini all models failed: %s — using fallback", last_err)
    return _tool_ai_fallback(user_msg), False


# ---------------------------------------------------------------------------
# LangGraph 狀態定義
# ---------------------------------------------------------------------------

class RouterState(TypedDict, total=False):
    thread_id: str
    role_id: str
    user_message: str
    chat_history: list | None       # 近期對話紀錄，供工具型 AI 保持連貫
    intent_vector: dict | None
    eguard_result: dict | None
    active_experts: list
    role_rules: list
    route_decision: dict | None
    persona_response: str | None
    split_messages: list | None     # [W6] 多氣泡序列 [{content, delay_ms}]
    suggest_match: bool | None      # 工具型 AI 偵測到建議配對時為 True
    observer_extractions: list | None
    implicit_state: str | None
    active_goals: list | None       # [R03 §3] 傳入 persona prompt 的目標清單
    upcoming_promises: list | None  # [R03 §3] 傳入 persona prompt 的承諾清單
    error: str | None


# ---------------------------------------------------------------------------
# LangGraph 節點
# ---------------------------------------------------------------------------

async def drift_validate_node(state: RouterState) -> RouterState:
    """[R02 §DRIFT] 第一道安全閘門。"""
    user_msg = state.get("user_message", "")
    result = drift_validate(user_msg, source="user")
    return {**state, "eguard_result": {
        "blocked": result.blocked,
        "reason": result.reason,
        "risk_score": result.risk_score,
    }}


async def rule_router_node(state: RouterState) -> RouterState:
    """[R09 §6.1] M4.1.1 信心分層路由。
    若前端已明確指定 persona（frontend_explicit），直接使用，不重新路由。
    """
    existing = state.get("route_decision") or {}
    if existing.get("route_reason") == "frontend_explicit":
        return state  # respect frontend's explicit expert selection

    decision = await route_with_confidence(
        user_msg=state.get("user_message", ""),
        intent_vector=state.get("intent_vector") or {},
        active_experts=state.get("active_experts") or [],
        role_id=state.get("role_id", ""),
        role_rules=state.get("role_rules") or [],
    )
    return {**state, "route_decision": {
        "persona_id": decision.persona_id,
        "route_reason": decision.route_reason,
        "confidence": decision.confidence,
        "thread_id": decision.thread_id,
    }}


async def invoke_persona_node(state: RouterState) -> RouterState:
    """
    M4.1.2 Persona 容器 + Observer 非同步派發。

    工具型 AI（tool_ai_default）呼叫 Gemini 生成真實對話，並偵測配對時機。
    Persona 走 M4.2 狀態機；Observer 以 create_task 背景執行，不阻塞回應。
    """
    decision = state.get("route_decision") or {}
    persona_id = decision.get("persona_id", "tool_ai_default")
    user_msg = state.get("user_message", "")
    active_experts = state.get("active_experts") or []

    # [Observer] 非同步派發，不阻塞主流程
    asyncio.create_task(_dispatch_observer_bg(state))

    # [Tool AI path] 呼叫 Gemini 生成真實對話 + 偵測配對時機
    if not persona_id or persona_id == "tool_ai_default":
        history = state.get("chat_history") or []
        reply, suggest_match = await _tool_ai_reply_gemini(user_msg, active_experts, history)
        return {**state, "persona_response": reply, "suggest_match": suggest_match}

    # [Persona path] M4.2 狀態機
    expert = next(
        (e for e in active_experts if str(e.get("id")) == str(persona_id)),
        None,
    )
    if not expert:
        expert = {
            "name": "AI 幫手",
            "personality_prompt": "你是一個有幫助、親切的 AI 助手，以繁體中文回答。",
            "tone_default": "empathetic",
            "trust_level": 0.5,
            "backstory": "",
        }

    persona_input = {
        "thread_id": state.get("thread_id"),
        "role_id": state.get("role_id"),
        "user_message": user_msg,
        "persona_id": persona_id,
        "persona_config": {
            "name": expert.get("name"),
            "personality_prompt": expert.get("personality_prompt"),
            "backstory": expert.get("backstory"),
            "tone_default": expert.get("tone_default", "empathetic"),
            "trust_level": expert.get("trust_level", 0.7),
            "persona_card": expert.get("persona_card"),  # [W3] PersonaCard v2 JSON
        },
        "implicit_state": state.get("implicit_state"),
        "chat_history": state.get("chat_history") or [],
        "bdi_belief": "",
        "bdi_desire": "",
        "current_tone": expert.get("tone_default", "empathetic"),
        "current_agency": expert.get("trust_level", 0.7),
        # [R03 §3] 目標與承諾注入記憶區塊，讓專家能追蹤使用者進度
        "active_goals": state.get("active_goals") or [],
        "upcoming_promises": state.get("upcoming_promises") or [],
    }

    try:
        persona_graph = get_persona_graph()
        res = await persona_graph.ainvoke(persona_input)
        response = res.get("final_response") or res.get("raw_response")
    except Exception as e:
        logger.warning("[M4.1.2] Persona graph failed: %s — using tool fallback", e)
        response = None

    if not response:
        response = _tool_ai_fallback(user_msg)

    # [W6] Propagate split_messages from M4.2 persona graph
    split_msgs = res.get("split_messages") if res else None
    return {**state, "persona_response": response, "split_messages": split_msgs, "suggest_match": False}


async def _dispatch_observer_bg(state: RouterState) -> None:
    """[M4.1.3] Observer 背景派發，silently fail。"""
    try:
        from .observer_dispatch import dispatch_observer
        await dispatch_observer(state)
    except Exception as e:
        logger.warning("[M4.1.3] observer dispatch failed: %s", e)


# ---------------------------------------------------------------------------
# 條件分支函數
# ---------------------------------------------------------------------------

def drift_decision(state: RouterState) -> str:
    eguard = state.get("eguard_result") or {}
    return "blocked" if eguard.get("blocked") else "passed"


# ---------------------------------------------------------------------------
# 圖構建（簡化：移除 observer_dispatch 節點，改為 invoke_persona_node 內部觸發）
# ---------------------------------------------------------------------------

def build_router_graph() -> StateGraph:
    """
    [R09: MAS §6.1] 線性圖：drift_guard → rule_router → persona_container → END
    Observer 在 persona_container 內以 create_task 非同步觸發，不佔 graph 邊。
    """
    graph = StateGraph(RouterState)

    graph.add_node("drift_guard", drift_validate_node)
    graph.add_node("rule_router", rule_router_node)
    graph.add_node("persona_container", invoke_persona_node)

    graph.set_entry_point("drift_guard")
    graph.add_conditional_edges("drift_guard", drift_decision, {
        "blocked": END,
        "passed": "rule_router",
    })
    graph.add_edge("rule_router", "persona_container")
    graph.add_edge("persona_container", END)

    return graph.compile()


_compiled_graph = None


def get_router_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_router_graph()
    return _compiled_graph
