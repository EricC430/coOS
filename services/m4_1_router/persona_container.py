"""
M4.1.2 -- Persona Agent 容器 (純結構接點)

SPEC: docs/modules/M4_1_agent_router_SPEC.md §7.1
Research: [R03 §1 微觀認知架構 LangGraph]
Note: 此容器不含任何 Persona 內容，Prompt 由 M4.2 注入。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonaAgentContainer:
    """
    [R03 §1] LangGraph Persona Agent 容器。
    system_prompt 永遠為 None，等待 M4.2 注入。
    """
    persona_id: str
    system_prompt: str | None = None
    awaits_prompt_injection: bool = True
    thread_id: str | None = None

    def inject_prompt(self, prompt: str) -> None:
        """由 M4.2 呼叫，注入 Persona 系統提示詞。"""
        self.system_prompt = prompt
        self.awaits_prompt_injection = False
