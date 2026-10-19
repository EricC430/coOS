import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

from .archetypes import CORE_ARCHETYPES, ArchetypeEvalRule

logger = logging.getLogger(__name__)


@dataclass
class FastPathResult:
    is_matched: bool
    achievement_id: str
    matched_keywords: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


@dataclass
class SlowPathAnalysisResult:
    concept_leap_depth: float
    proactivity_score: float
    themes: List[str] = field(default_factory=list)
    summary: str = ""
    is_epistemic_spark: bool = False


class FastPathMatcher:
    """
    快軌 (Fast Path) 輕量正則與關鍵字比對器.
    目標延遲 < 100ms，在主執行緒無感監聽對話。
    """

    def __init__(self):
        # 預編譯正則表達式以求最高速度
        self._compiled_rules: dict[str, list[re.Pattern]] = {}
        for ach_id, rule in CORE_ARCHETYPES.items():
            self._compiled_rules[ach_id] = [
                re.compile(p, re.IGNORECASE) for p in rule.regex_patterns
            ]

    def evaluate(self, text: str, achievement_id: str) -> FastPathResult:
        start_time = time.perf_counter()
        patterns = self._compiled_rules.get(achievement_id, [])

        if not patterns or not text:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return FastPathResult(
                is_matched=False,
                achievement_id=achievement_id,
                execution_time_ms=elapsed_ms,
            )

        matched_keywords: List[str] = []
        all_patterns_matched = True

        for pat in patterns:
            match = pat.search(text)
            if match:
                matched_keywords.append(match.group(0))
            else:
                all_patterns_matched = False

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return FastPathResult(
            is_matched=all_patterns_matched and len(matched_keywords) > 0,
            achievement_id=achievement_id,
            matched_keywords=matched_keywords,
            execution_time_ms=elapsed_ms,
        )

    def scan_all_archetypes(self, text: str) -> List[FastPathResult]:
        """對所有核心原型執行快軌掃描，回傳所有命中的候選成就."""
        results = []
        for ach_id in CORE_ARCHETYPES.keys():
            res = self.evaluate(text, ach_id)
            if res.is_matched:
                results.append(res)
        return results


class SlowPathAnalyzer:
    """
    慢軌 (Slow Path) 本機 Gemma (M2.2) 深度語意分析解析器.
    評估認知跳躍深度 (concept_leap_depth) 與主動提問權重 (proactivity_score).
    嚴格遵守逾時限制（預設 3 秒），超時則拋出 TimeoutError 由離線佇列接管。
    """

    def __init__(self, timeout_seconds: float = 3.0, simulate_timeout: bool = False):
        self.timeout_seconds = timeout_seconds
        self.simulate_timeout = simulate_timeout

    async def analyze_epistemic_depth(
        self, text: str, role_id: Optional[str] = None
    ) -> SlowPathAnalysisResult:
        if self.simulate_timeout:
            # 模擬 Gemma 離線或推論逾時
            await asyncio.sleep(self.timeout_seconds + 0.05)
            raise asyncio.TimeoutError("Local Gemma inference timed out or is offline")

        start_time = time.perf_counter()

        try:
            return await asyncio.wait_for(
                self._run_inference(text, role_id),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(f"[M4.12 SlowPath] Gemma inference timed out (> {self.timeout_seconds}s)")
            raise

    async def _run_inference(
        self, text: str, role_id: Optional[str]
    ) -> SlowPathAnalysisResult:
        # 模擬本地 Gemma 認知深度打分邏輯
        # 實際整合時可呼叫 M2.2 Local LLM API
        await asyncio.sleep(0.02)  # 微延遲模擬本地推論

        concept_leap = 0.30
        proactivity = 0.40
        themes: List[str] = []

        # 認知跳躍特徵識別 (Concept Leap Indicators)
        leap_indicators = [
            "底層", "架構", "原理", "CAP", "分散式", "抽象", "SSA", "編譯器",
            "重構", "薩提爾", "脆弱", "心態", "接納", "轉念", "跨領域", "融通"
        ]
        proactivity_indicators = [
            "為什麼", "如何實現", "發現", "畫了", "探索", "我想理解", "根本權衡", "對照"
        ]

        found_leap = [ind for ind in leap_indicators if ind in text]
        found_proactive = [ind for ind in proactivity_indicators if ind in text]

        if found_leap:
            concept_leap += min(0.60, len(found_leap) * 0.20)
            themes.extend(found_leap)

        if found_proactive:
            proactivity += min(0.55, len(found_proactive) * 0.20)

        # 額外考量字串長度與提問語氣
        if "?" in text or "？" in text:
            proactivity += 0.10

        concept_leap = min(1.0, concept_leap)
        proactivity = min(1.0, proactivity)

        is_spark = concept_leap >= 0.60 and proactivity >= 0.70
        summary = f"識別認知特徵: {', '.join(themes[:3])}" if themes else "常規探討"

        return SlowPathAnalysisResult(
            concept_leap_depth=round(concept_leap, 2),
            proactivity_score=round(proactivity, 2),
            themes=themes,
            summary=summary,
            is_epistemic_spark=is_spark,
        )


async def generate_personalized_flavor_text(
    rule: ArchetypeEvalRule,
    user_excerpt: str,
    themes: List[str],
    role_id: Optional[str] = None,
) -> tuple[str, str]:
    """
    T027: 本機 Gemma 個性化副稱號與啟發金句（flavor_text）生成與 context_summary 封裝.
    """
    await asyncio.sleep(0.01)
    theme_desc = "、".join(themes[:3]) if themes else "深邃思考"
    template = rule.flavor_text_template.strip()

    if "。" in template:
        prefix, suffix = template.rsplit("。", 1)
        flavor_text = f"{prefix}，在探究「{theme_desc}」的旅程中，光芒已然照亮前路。{suffix}"
    else:
        flavor_text = f"「於【{theme_desc}】中，{template.strip('「」')}」"

    context_summary = f"於 {role_id or '自主探索'} 領域體悟: {user_excerpt[:80]}"
    return flavor_text, context_summary

