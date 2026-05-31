"""M2.2 GemmaEdgeClient -- httpx client for iPad ai.local Ollama API

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1 §7.1, §7.2
[R07: POST §4.3] POST framework system prompt for privacy-preserving compression

Endpoint: POST {ai_local_host}/api/chat
Model: gemma-4-e4b-it-4bit (Ollama-compatible)
Timeout: 6s (SPEC §7.4 latency target)
"""

from __future__ import annotations

import json

import httpx

POST_SYSTEM_PROMPT = (
    "You are a privacy-preserving semantic compression customs officer. "
    "Your task is to read the user's raw activity log or code and output a "
    "de-identified intent label in JSON format.\n"
    "You MUST:\n"
    "1. Remove all PII: filenames, variable names, IPs, URLs, DB column names.\n"
    "2. Generalize concrete actions (e.g. 'editing db.py SQL' -> 'database write development').\n"
    "3. Estimate emotional state (e.g. long retry loops -> frustration; clean compile -> flow).\n"
    "Output strictly valid JSON with keys: "
    "intent_label, context_summary, frustration_level (0.0-1.0), "
    "valence (-1.0 to 1.0), arousal (0.0-1.0), stripped_entities_count."
)


class GemmaEdgeClient:
    """Thin httpx wrapper for the iPad Ollama inference endpoint.

    anti-pattern: do NOT send concurrent requests -- always serialized via
    InferencePriorityQueue in pipeline.py (SPEC §8 anti-pattern 2).
    """

    def __init__(self, ai_local_host: str, model: str, timeout: float = 6.0) -> None:
        self._base_url = ai_local_host.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def generate(self, user_text: str) -> dict:
        """Send text to Gemma via Ollama /api/chat and return parsed JSON dict.

        Raises:
            httpx.TimeoutException: if inference exceeds timeout (triggers circuit breaker)
            httpx.ConnectError: if ai.local unreachable (triggers fallback mode)
            ValueError: if response JSON is malformed
        """
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": POST_SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("message", {}).get("content", "")
        # Gemma sometimes wraps JSON in markdown fences
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
        return json.loads(content)
