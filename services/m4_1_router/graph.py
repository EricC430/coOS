"""
M4.1 -- LangGraph 頂層協調圖

SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.1
Research: [R09: MAS §6.1] 多智能體頂層協調圖 (含安全過濾與信心分流)
         [R03 §1] Persona Agent 容器的 LangGraph 節點結構
"""
from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .drift import drift_validate
from .observer_dispatch import dispatch_observer
from .routing_engine import route_with_confidence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph 狀態定義
# ---------------------------------------------------------------------------

class RouterState(TypedDict, total=False):
    thread_id: str
    role_id: str
    user_message: str
    intent_vector: dict | None        # M2.2 輸出
    eguard_result: dict | None        # M2.3 輸出
    active_experts: list                 # M4.3 白名單
    role_rules: list                     # M6.x role_router_rules 熱載入
    route_decision: dict | None       # M4.1.1 輸出
    persona_response: str | None      # M4.2 填入
    observer_extractions: list | None # M4.1.3/M4.6 填入
    error: str | None


# ---------------------------------------------------------------------------
# LangGraph 節點
# ---------------------------------------------------------------------------

async def drift_validate_node(state: RouterState) -> RouterState:
    """
    [R02 §DRIFT] 第一道安全閘門。
    fail-closed：eguard_result.blocked=True 時在 drift_decision 中直接 END。
    """
    user_msg = state.get("user_message", "")
    result = drift_validate(user_msg, source="user")
    return {**state, "eguard_result": {
        "blocked": result.blocked,
        "reason": result.reason,
        "risk_score": result.risk_score,
    }}


async def rule_router_node(state: RouterState) -> RouterState:
    """
    [R09 §6.1] M4.1.1 信心分層路由。
    結果寫入 state["route_decision"]。
    """
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


async def llm_router_node(state: RouterState) -> RouterState:
    """低信心時由 LLM 主導路由（route_with_confidence 內部已處理，此節點為備用接點）。"""
    return state


async def invoke_persona_node(state: RouterState) -> RouterState:
    """
    M4.1.2 純結構接點：轉發到對應 Persona 容器。
    Prompt 內容由 M4.2 注入，此節點不含任何 Persona 內容。
    """
    decision = state.get("route_decision") or {}
    logger.debug("[M4.1.2] Persona container: %s", decision.get("persona_id"))
    # M4.2 實作後此處替換為真實 Persona 呼叫
    return {**state, "persona_response": None}


# ---------------------------------------------------------------------------
# 條件分支函數
# ---------------------------------------------------------------------------

def drift_decision(state: RouterState) -> str:
    """DRIFT 安全閘：blocked -> END, passed -> rule_router"""
    eguard = state.get("eguard_result") or {}
    if eguard.get("blocked"):
        return "blocked"
    return "passed"


def confidence_branch(state: RouterState) -> str:
    """根據路由信心度分流"""
    decision = state.get("route_decision") or {}
    conf = decision.get("confidence", 0.0)
    if conf >= 0.85:
        return "high"
    if conf >= 0.50:
        return "mid"
    return "low"


# ---------------------------------------------------------------------------
# 圖構建
# ---------------------------------------------------------------------------

def build_router_graph() -> StateGraph:
    """
    [R09: MAS §6.1] 建構 LangGraph 多智能體頂層協調圖。
    """
    graph = StateGraph(RouterState)

    graph.add_node("drift_guard", drift_validate_node)
    graph.add_node("rule_router", rule_router_node)
    graph.add_node("llm_router", llm_router_node)
    graph.add_node("persona_container", invoke_persona_node)
    graph.add_node("observer_dispatch", dispatch_observer)

    graph.set_entry_point("drift_guard")
    graph.add_conditional_edges("drift_guard", drift_decision, {
        "blocked": END,
        "passed": "rule_router",
    })
    graph.add_conditional_edges("rule_router", confidence_branch, {
        "high": "persona_container",
        "mid": "persona_container",
        "low": "llm_router",
    })
    graph.add_edge("llm_router", "persona_container")
    graph.add_edge("persona_container", END)
    graph.add_edge("rule_router", "observer_dispatch")
    graph.add_edge("observer_dispatch", END)

    return graph.compile()


# 模組層級預編譯圖（lazy，僅需要時才建立）
_compiled_graph = None


def get_router_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_router_graph()
    return _compiled_graph
