"""M2.2 GemmaInferencePipeline -- compress raw text to IntentVector

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.1-7.5
[R07: POST §4.3] hard-prompted semantic translation (engineering deviation from soft-prompt)
[R07: 意圖向量 §4.4] structured JSON + sentence embedding (engineering deviation from tensor)
RISK-05: source_log_id and role_id are mandatory even in fallback mode
RISK-11: RAM check before loading model -- handled by caller (OS-level check)
"""

from __future__ import annotations

import httpx

from .client import GemmaEdgeClient
from .fallback import RuleBasedExtractor
from .schema import IntentVector

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
        ai_local_host: str = "http://ai.local:11434",
        model: str = "gemma-4-e4b-it-4bit",
        timeout: float = 15.0,  # revised: Ollama overhead on iPad M1 ~11-12s actual
    ) -> None:
        self._client = GemmaEdgeClient(ai_local_host, model, timeout)
        self.fallback = RuleBasedExtractor()
        self._edge_offline = False  # toggled by simulate_edge_offline() in tests

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
        if self._edge_offline:
            return self._make_fallback_vector(source_log_id, role_id)

        try:
            raw = await self._client.generate(text)
            return IntentVector(
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
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, ValueError):  # noqa: BLE001
            # Circuit breaker: degrade gracefully (RISK-11 safeguard)
            return self._make_fallback_vector(source_log_id, role_id)

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
