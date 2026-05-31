"""M2.2 Gemma Edge Inference Pipeline

SPEC: docs/modules/M2_2_gemma_edge_inference_SPEC.md v1.1
[R07: POST §4.3] local SLM compresses raw text -> intent vector, never sends plaintext to cloud
[R06: §7.4 差分隱私] intent vector is de-identified before leaving device
"""
from .pipeline import GemmaInferencePipeline
from .schema import IntentVector

__all__ = ["GemmaInferencePipeline", "IntentVector"]
