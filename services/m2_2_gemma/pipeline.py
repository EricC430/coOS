"""M2.2 GemmaInferencePipeline -- compress raw text to IntentVector

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.1-7.5
[R07: POST §4.3] hard-prompted semantic translation (engineering deviation from soft-prompt)
[R07: 意圖向量 §4.4] structured JSON + sentence embedding (engineering deviation from tensor)
RISK-05: source_log_id and role_id are mandatory even in fallback mode
RISK-11: RAM check before loading model -- handled by caller (OS-level check)
"""

from __future__ import annotations

import logging
import re
import time
import httpx

from .client import GemmaEdgeClient
from .fallback import RuleBasedExtractor
from .schema import IntentVector

logger = logging.getLogger(__name__)

# Circuit breaker sentinel
_FALLBACK_LABEL = "unknown_ambient_activity"


class GemmaInferencePipeline:
    """Main entry point for M2.2.

    Usage:
        pipeline = GemmaInferencePipeline(ai_local_host="http://ai.local:11434",
                                          model="gemma-4-e4b-it-4bit")
        vector = await pipeline.compress("raw text", source_log_id="...", role_id="...")
    """

    def __init__(
        self,
        ai_local_host: str = "http://192.168.0.79:11434",
        model: str = "gemma-4-e4b-it-4bit",
        timeout: float = 90.0,  # iPad M1 can take 15-60s for 200-300 tokens
    ) -> None:
        self._client = GemmaEdgeClient(ai_local_host, model, timeout)
        self.fallback = RuleBasedExtractor()
        self._edge_offline = False  # toggled by simulate_edge_offline() in tests
        self._locality_cache: dict[tuple[str, str, str], tuple[float, str, IntentVector]] = {}

    def _extract_cache_key(self, text: str, role_id: str) -> tuple[str, str, str]:
        # Try to find app name and window title from JSON summary
        apps = re.findall(r'"app_name":\s*"([^"]+)"', text)
        titles = re.findall(r'"window_title":\s*"([^"]+)"', text)
        
        # If not JSON, try raw text tags like [TITLE]
        if not apps:
            app_match = re.search(r'\[TITLE\]\s*(.*?)\s*(?:\n|$)', text)
            if app_match:
                title_val = app_match.group(1).strip()
                # Split on common separators like - to guess app name
                parts = title_val.split(" - ")
                app_key = parts[-1].strip() if len(parts) > 1 else title_val
                title_key = title_val
            else:
                app_key = "raw_content"
                title_key = text[:100].strip()  # first 100 chars as key
        else:
            app_key = apps[0]
            title_key = titles[0] if titles else ""
            
        return (role_id, app_key, title_key)

    def _text_similarity(self, s1: str, s2: str) -> float:
        # Lightweight Jaccard similarity based on alphanumeric words
        words1 = set(re.findall(r'\w+', s1.lower()))
        words2 = set(re.findall(r'\w+', s2.lower()))
        if not words1 and not words2:
            return 1.0
        return len(words1.intersection(words2)) / len(words1.union(words2))

    async def compress(
        self,
        text: str,
        source_log_id: str,
        role_id: str,
    ) -> IntentVector:
        """Compress raw text to a de-identified IntentVector.

        Tries Gemma edge first; falls back to RuleBasedExtractor on any error.
        RISK-05: source_log_id and role_id are always set regardless of mode.
        """
        # 1. Check Locality Cache
        cache_key = self._extract_cache_key(text, role_id)
        now = time.monotonic()
        if cache_key in self._locality_cache:
            ts, cached_text, cached_vector = self._locality_cache[cache_key]
            if now - ts < 90.0:  # 90 seconds (1.5 minutes) TTL
                similarity = self._text_similarity(text, cached_text)
                if similarity >= 0.75:
                    logger.info(
                        "[M2.2] Locality cache hit for key: %s (similarity: %.2f, TTL remaining: %.1fs)",
                        cache_key,
                        similarity,
                        90.0 - (now - ts),
                    )
                    return IntentVector(
                        source_log_id=source_log_id,
                        role_id=role_id,
                        intent_label=cached_vector.intent_label,
                        context_summary=cached_vector.context_summary,
                        frustration_level=cached_vector.frustration_level,
                        valence=cached_vector.valence,
                        arousal=cached_vector.arousal,
                        stripped_entities_count=cached_vector.stripped_entities_count,
                        semantic_embedding=cached_vector.semantic_embedding,
                        inference_mode="locality_hit",
                    )
                else:
                    logger.info(
                        "[M2.2] Locality cache miss due to low content similarity: %.2f for key: %s",
                        similarity,
                        cache_key,
                    )

        if self._edge_offline:
            return self._make_fallback_vector(text, source_log_id, role_id)

        try:
            raw = await self._client.generate(text, role_id=role_id, correlation_id=source_log_id)
            vector = IntentVector(
                source_log_id=source_log_id,
                role_id=role_id,
                intent_label=str(raw.get("intent_label", _FALLBACK_LABEL)),
                context_summary=str(raw.get("context_summary", "")),
                frustration_level=float(raw.get("frustration_level", 0.0)),
                valence=float(raw.get("valence", 0.0)),
                arousal=float(raw.get("arousal", 0.0)),
                stripped_entities_count=int(raw.get("stripped_entities_count", 0)),
                semantic_embedding=raw.get("semantic_embedding", []),
                inference_mode="gemma_edge",
            )
            # Update Locality Cache on successful edge inference
            self._locality_cache[cache_key] = (now, text, vector)
            return vector
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, ValueError):  # noqa: BLE001
            # Circuit breaker: degrade gracefully (RISK-11 safeguard)
            return self._make_fallback_vector(text, source_log_id, role_id)

    def _make_fallback_vector(self, text: str, source_log_id: str, role_id: str) -> IntentVector:
        """Rule-based fallback -- RISK-05: source_log_id/role_id always preserved."""
        extracted = self.fallback.extract(text)
        return IntentVector(
            source_log_id=source_log_id,
            role_id=role_id,
            inference_mode="rule_based_fallback",
            **extracted,
        )

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def simulate_edge_offline(self) -> None:
        """Force fallback mode for testing without a real iPad."""
        self._edge_offline = True

    def simulate_edge_online(self) -> None:
        self._edge_offline = False
