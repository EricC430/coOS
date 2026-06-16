"""
M4.1.4 -- DRIFT 安全規劃器

SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.3
Research: [R02: DRIFT §架構安全性] 動態規則隔離框架
Risk: fail-closed (SPEC §9 拍板)
"""
import re
from dataclasses import dataclass


@dataclass
class DRIFTResult:
    blocked: bool
    reason: str
    risk_score: float  # 0.0~1.0


# [R02: DRIFT §架構安全性] 已知注入模式 (持續更新)
_INJECTION_PATTERNS = [
    r"忽略.*(?:以上|之前|所有).*(?:指令|提示|規則)",
    r"(?:你現在是|你的新角色是|從現在起你是)",
    r"(?:ignore|disregard).*(?:previous|above).*(?:instructions?|prompts?)",
    r"(?:system|admin)\s*(?:override|mode|access)",
    r"<\s*(?:system|prompt|instruction)\s*>",
    r"act\s+as\s+(?:dan|jailbreak|unrestricted)",
    # [W9.7] 新增常見 jailbreak 變體
    r"do\s+anything\s+now",
    r"roleplay\s+as\s+(?:a\s+)?(?:evil|unrestricted|unfiltered)",
    r"(?:假裝|扮演).*(?:沒有限制|壞人|邪惡)",
    r"(?:bypass|circumvent|override)\s+(?:safety|filter|content)",
    r"(?:你沒有|取消).*(?:限制|規則|安全)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def drift_validate(user_msg: str, source: str = "user") -> DRIFTResult:
    """
    [R02 §DRIFT] 驗證輸入是否含有 Prompt Injection 嘗試。

    外部 Git Commit (M1.4) 字串風險更高，閾值從 0.8 降至 0.5。
    採 fail-closed：引擎崩潰時視為 blocked。
    """
    risk_score = 0.0
    for pattern in _COMPILED:
        if pattern.search(user_msg):
            risk_score = max(risk_score, 0.9)
            break

    threshold = 0.5 if source == "external_git" else 0.8

    if risk_score >= threshold:
        return DRIFTResult(blocked=True, reason="prompt_injection_detected", risk_score=risk_score)
    return DRIFTResult(blocked=False, reason="passed", risk_score=risk_score)
