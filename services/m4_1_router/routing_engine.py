"""
M4.1.1 -- 信心分層路由引擎 (三層決策架構)

SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.2
Research: [R09: MAS §6.1] 三層決策: Rule -> LLM 背景驗證 -> LLM 主導
Risk: RISK-06 (角色隔離), RISK-13a (no raw msg), RISK-14a (no raw msg to LLM)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 信心分閾值 (SPEC §7.2 + docs/02_architecture.md 決策 B1)
# ---------------------------------------------------------------------------
CONF_HIGH = 0.85  # >= 此值直接採用 rule，不觸發 LLM
CONF_MID = 0.50   # 0.50~0.85: rule 先回，背景 LLM 驗證


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RouteDecision:
    persona_id: str
    route_reason: str
    thread_id: str
    confidence: float  # 0.0~1.0，透明傳遞給前端 SSE


@dataclass
class RoleContext:
    role_id: str
    role_slug: str
    active_experts: list[dict]  # [RISK-06] M4.3 提供的白名單


# ---------------------------------------------------------------------------
# [5.1 LLM Tiering] 模型難度對照表
# ---------------------------------------------------------------------------
MODEL_MAP: dict[str, list[str]] = {
    "tier1": ["gemma-4-31b", "gemma-4-26b"],
    "tier2": ["gemini-2.0-flash-lite", "gemma-4-31b"],
    "tier3": ["gemini-2.0-flash", "gemini-2.0-flash-lite"],
    "tier4": ["gemini-2.5-pro", "gemini-2.0-flash"],
}


class RateLimitError(Exception):
    pass


class ServiceUnavailableError(Exception):
    pass


def get_cloud_llm_client(model_name: str):
    """Return a simple async LLM client wrapper for the given model."""
    return _CloudLLMClient(model_name)


class _CloudLLMClient:
    """Thin wrapper around google.genai for routing LLM calls."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    async def complete(self, prompt: str) -> str:
        import os
        try:
            from google import genai  # type: ignore
        except ImportError:
            raise ImportError("google.genai not available, use langchain fallback")

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ServiceUnavailableError("GEMINI_API_KEY not set")

        client = genai.Client(api_key=api_key)
        resp = await asyncio.to_thread(
            client.models.generate_content,
            model=self.model_name,
            contents=prompt,
        )
        return resp.text.strip()


async def call_cloud_llm_with_fallback(prompt: str, task_difficulty: str) -> str:
    """
    [5.1 LLM Tiering] 根據任務難度選擇優先模型，遇到 429/503 自動降級。
    """
    models = MODEL_MAP.get(task_difficulty, ["gemini-2.0-flash"])
    last_err: Exception | None = None
    for model_name in models:
        try:
            client = get_cloud_llm_client(model_name)
            response = await client.complete(prompt)
            return response
        except (RateLimitError, ServiceUnavailableError, httpx.HTTPStatusError) as e:
            logger.warning("[M4.1.1] Model %s failed: %s. Trying next.", model_name, e)
            last_err = e
    raise last_err or RuntimeError("All model tiers failed")


# ---------------------------------------------------------------------------
# 信心分計算
# ---------------------------------------------------------------------------

def _compute_confidence(keyword_match: bool, intent_match: bool, hit_count: int) -> float:
    """信心分三信號加權求和，上限 1.0。"""
    base = 0.0
    if keyword_match:
        base += 0.60
    if intent_match:
        base += 0.25
    history_bonus = min(hit_count / 20, 0.15)
    return min(base + history_bonus, 1.0)


# ---------------------------------------------------------------------------
# Rule-based 路由
# ---------------------------------------------------------------------------

def _find_expert_by_intent(intent_label: str, active_experts: list[dict]) -> str | None:
    """將 intent_label 比對 expert 的 domain 或 domain_keywords。"""
    for expert in active_experts:
        domain = expert.get("domain", "")
        keywords = expert.get("domain_keywords", [])
        if intent_label == domain or intent_label in keywords:
            return expert["id"]
        if any(kw.lower() in intent_label.lower() for kw in keywords):
            return expert["id"]
    return None


def _find_expert_by_domain(domain: str, active_experts: list[dict]) -> str | None:
    """LLM 路由回傳 domain 字串後，映射回 expert id。"""
    for expert in active_experts:
        if expert.get("domain") == domain:
            return expert["id"]
        if any(kw.lower() in domain.lower() for kw in expert.get("domain_keywords", [])):
            return expert["id"]
    return None


def _rule_based_route(
    user_msg: str,
    intent_vector: dict,
    active_experts: list[dict],
    role_rules: list[dict],
) -> RouteDecision:
    """
    [R09 §6.1] 三層優先：DB 規則 -> 意圖向量 -> Fallback 工具型 AI
    [RISK-06] 只允許 active_experts 白名單內的 persona_id 通過
    """
    active_expert_ids = {e["id"] for e in active_experts}
    best: RouteDecision | None = None

    # 1. role_router_rules 正則匹配
    for rule in sorted(role_rules, key=lambda r: r.get("confidence", 0.5), reverse=True):
        if rule.get("status") != "active":
            continue
        # [RISK-06] persona 必須在白名單內
        if rule.get("persona_id") not in active_expert_ids:
            continue
        try:
            if re.search(rule["pattern"], user_msg, re.IGNORECASE):
                computed = _compute_confidence(
                    keyword_match=True,
                    intent_match=False,
                    hit_count=rule.get("hit_count", 0),
                )
                # 取計算值與 DB 規則已校正信心分的較大值
                conf = max(computed, rule.get("confidence", 0.0))
                if best is None or conf > best.confidence:
                    best = RouteDecision(
                        persona_id=rule["persona_id"],
                        route_reason=f"keyword:{rule.get('target_domain', rule['id'])}",
                        thread_id="",
                        confidence=conf,
                    )
        except re.error:
            logger.warning(
                "[M4.1.1] Invalid regex in rule %s: %s",
                rule.get("id"), rule.get("pattern"),
            )

    if best and best.confidence >= CONF_MID:
        return best

    # 2. 意圖向量兜底
    if intent_vector and intent_vector.get("intent_label"):
        matched_id = _find_expert_by_intent(intent_vector["intent_label"], active_experts)
        if matched_id:
            conf = _compute_confidence(keyword_match=False, intent_match=True, hit_count=0)
            if best is None or conf > best.confidence:
                best = RouteDecision(
                    persona_id=matched_id,
                    route_reason=f"intent_vector:{intent_vector['intent_label']}",
                    thread_id="",
                    confidence=conf,
                )

    if best:
        return best

    # 3. Fallback
    return RouteDecision(
        persona_id="tool_ai_default",
        route_reason="no_match_fallback",
        thread_id="",
        confidence=0.30,
    )


# ---------------------------------------------------------------------------
# LLM 路由
# ---------------------------------------------------------------------------

async def llm_route(
    intent_vector: dict,
    active_experts: list[dict],
    role_id: str,
    task_difficulty: str = "tier3",
) -> RouteDecision:
    """
    [RISK-14a] LLM 補判只傳 intent_vector + expert domains，不傳原始訊息。
    [5.1 LLM Tiering] 主要路由為 Tier 3，背景驗證為 Tier 2。
    """
    expert_domains = [e.get("domain", "") for e in active_experts]
    prompt = (
        f"Route this conversation to the most appropriate expert.\n"
        f"Intent vector: {intent_vector}\n"
        f"Available expert domains: {expert_domains}\n"
        f"Reply with ONLY the domain name."
    )
    try:
        domain = await call_cloud_llm_with_fallback(prompt, task_difficulty=task_difficulty)
    except Exception as e:
        logger.error("[M4.1.1] Cloud routing failed: %s. Using default tool.", e)
        return RouteDecision(
            persona_id="tool_ai_default",
            route_reason="llm_route_failed_fallback",
            thread_id="",
            confidence=0.10,
        )

    matched = _find_expert_by_domain(domain, active_experts)
    return RouteDecision(
        persona_id=matched or "tool_ai_default",
        route_reason=f"llm_primary:{domain}",
        thread_id="",
        confidence=0.75,
    )


async def llm_verify_and_learn(
    user_msg: str,
    rule_decision: RouteDecision,
    active_experts: list[dict],
    role_id: str,
) -> None:
    """
    背景執行：LLM 驗證 rule 路由是否正確。
    [RISK-13a] user_msg 只取 hash，不傳原文給 LLM。
    [5.1 LLM Tiering] 背景驗證為 Tier 2。
    """
    try:
        llm_decision = await llm_route(
            intent_vector={"intent_label": "unknown"},
            active_experts=active_experts,
            role_id=role_id,
            task_difficulty="tier2",
        )
        agreed = llm_decision.persona_id == rule_decision.persona_id
        outcome = "llm_agree" if agreed else "llm_disagree"
        _log_sample(user_msg, rule_decision, role_id=role_id, outcome=outcome)
    except Exception as e:
        logger.warning("[M4.1.1] llm_verify_and_learn failed: %s", e)


# ---------------------------------------------------------------------------
# 路由樣本記錄 (RISK-13a)
# ---------------------------------------------------------------------------

def _extract_keyword_tokens(text: str) -> list[str]:
    """
    [RISK-13a] 提取 2~4 個有意義的詞，不含 PII。
    使用 jieba 分詞，濾掉單字元和常見停用詞。
    """
    try:
        import jieba  # type: ignore
        tokens = list(jieba.cut_for_search(text))
    except ImportError:
        tokens = re.findall(r"[一-鿿]{2,}|[a-zA-Z]{3,}", text)

    stopwords = {"的", "了", "嗎", "我", "你", "他", "是", "在", "有", "這", "那", "和"}
    filtered = [t.strip() for t in tokens if len(t.strip()) >= 2 and t.strip() not in stopwords]
    return filtered[:4]


def build_routing_sample(
    user_msg: str,
    decision: RouteDecision,
    outcome: str,
    role_id: str,
) -> dict:
    """
    [RISK-13a] 構建路由樣本 dict，只存 SHA-256 hash 和去 PII tokens，不存原文。
    """
    return {
        "user_msg_hash": hashlib.sha256(user_msg.encode()).hexdigest(),
        "keyword_tokens": _extract_keyword_tokens(user_msg),
        "rule_persona_id": decision.persona_id,
        "confidence": decision.confidence,
        "outcome": outcome,
        "role_id": role_id,
    }


def _log_sample(
    user_msg: str,
    decision: RouteDecision,
    role_id: str,
    outcome: str,
    **kwargs: Any,
) -> None:
    """非同步寫入 routing_samples（fire-and-forget）。"""
    sample = build_routing_sample(user_msg, decision, outcome, role_id)
    sample.update({k: str(v) for k, v in kwargs.items()})

    async def _write():
        try:
            import json
            import os
            import sqlite3
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "coos.db")
            conn = sqlite3.connect(db_path)
            conn.execute(
                "INSERT INTO routing_samples "
                "(role_id, user_msg_hash, keyword_tokens, rule_persona_id, confidence, outcome) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    sample["role_id"],
                    sample["user_msg_hash"],
                    json.dumps(sample["keyword_tokens"], ensure_ascii=False),
                    sample["rule_persona_id"],
                    sample["confidence"],
                    sample["outcome"],
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug("[M4.1.1] _log_sample write failed: %s", e)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_write())
    except RuntimeError:
        pass  # 非 async 上下文時靜默跳過


# ---------------------------------------------------------------------------
# 頂層路由入口
# ---------------------------------------------------------------------------

async def route_with_confidence(
    user_msg: str,
    intent_vector: dict,
    active_experts: list[dict],
    role_id: str,
    role_rules: list[dict],
) -> RouteDecision:
    """
    [R09 §6.1] 三層信心分路由入口。
    中高信心：使用者感受 0ms 延遲；LLM 僅在背景或低信心時介入。
    """
    rule_decision = _rule_based_route(user_msg, intent_vector, active_experts, role_rules)

    if rule_decision.confidence >= CONF_HIGH:
        _log_sample(user_msg, rule_decision, role_id=role_id, outcome="rule_high_conf")
        return rule_decision

    if rule_decision.confidence >= CONF_MID:
        # 背景非同步驗證，不阻塞主回應
        asyncio.create_task(
            llm_verify_and_learn(user_msg, rule_decision, active_experts, role_id)
        )
        _log_sample(user_msg, rule_decision, role_id=role_id, outcome="rule_mid_conf_llm_pending")
        return rule_decision

    # 低信心：LLM 主導
    llm_decision = await llm_route(intent_vector, active_experts, role_id)
    _log_sample(user_msg, llm_decision, role_id=role_id, outcome="llm_primary")
    return llm_decision
