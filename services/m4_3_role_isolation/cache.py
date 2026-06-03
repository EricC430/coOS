"""
M4.3.4 -- Prompt Cache (角色隔離快取層)

SPEC: docs/modules/M4_3_role_isolation_SPEC.md §7.3
Research: [R03 §6] 角色切換時 Persona 記憶必須完全重置
Risk: RISK-06 (跨角色快取殘留)
"""
from __future__ import annotations

import uuid
from typing import Any


class PromptCache:
    """
    [R03 §6] 以 (role_id, persona_id) 為鍵的系統提示詞快取。

    角色切換時呼叫 invalidate_by_role 清除整個角色的快取，
    確保舊角色的 Persona prompt 不會殘留。
    """

    def __init__(self) -> None:
        self._store: dict[tuple[uuid.UUID, str], Any] = {}

    def set(self, role_id: uuid.UUID, persona_id: str, prompt: str) -> None:
        self._store[(role_id, persona_id)] = prompt

    def get(self, role_id: uuid.UUID, persona_id: str) -> str | None:
        return self._store.get((role_id, persona_id))

    def invalidate_by_role(self, role_id: uuid.UUID) -> int:
        """清除指定角色的所有快取項目，回傳清除數量。"""
        keys_to_del = [k for k in self._store if k[0] == role_id]
        for k in keys_to_del:
            del self._store[k]
        return len(keys_to_del)

    def invalidate_by_persona(self, persona_id: uuid.UUID) -> int:
        """清除指定 Persona 的所有快取項目（跨角色），回傳清除數量。"""
        keys_to_del = [k for k in self._store if k[1] == str(persona_id)]
        for k in keys_to_del:
            del self._store[k]
        return len(keys_to_del)

    def clear_all(self) -> None:
        self._store.clear()


# 模組層級單例（FastAPI 使用）
_default_cache: PromptCache | None = None


def get_prompt_cache() -> PromptCache:
    global _default_cache
    if _default_cache is None:
        _default_cache = PromptCache()
    return _default_cache
