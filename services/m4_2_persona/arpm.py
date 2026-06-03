"""
M4.2 ARPM -- Adaptive Re-ranking Persona Memory 監督閘門

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.1 (arpm_audit 節點)
Research: [R03: §2 ARPM 框架] 異質時序記憶治理框架
Risk: RISK-02 (Echo Mode 切換不應觸發 ARPM 還原)
Note: M4.9 將提供完整 ARPM；此模組為 MVP 版本，僅做切換合法性驗證。
"""
from __future__ import annotations

from enum import Enum

from .echo_mode import LEGAL_TRANSITIONS, ToneState


class ValidationResult(str, Enum):
    LEGAL = "legal"
    DRIFT_DETECTED = "drift_detected"


class ARPMValidator:
    """
    [R03 §2] MVP ARPM：驗證 Persona 狀態切換是否合法。

    echo_mode_authorized=True 時，允許所有 LEGAL_TRANSITIONS 內的切換。
    echo_mode_authorized=False 時，僅允許相鄰一步切換；跨步切換 → DRIFT_DETECTED。
    """

    def validate(
        self,
        prev_state: ToneState,
        current_state: ToneState,
        echo_mode_authorized: bool = False,
    ) -> ValidationResult:
        """
        [R03 §2 ARPM] 驗證狀態切換是否合法。
        [RISK-02] echo_mode_authorized=True 時認得所有 LEGAL_TRANSITIONS 合法路徑。
        """
        if prev_state == current_state:
            return ValidationResult.LEGAL

        legal_targets = LEGAL_TRANSITIONS.get(prev_state, [])

        if echo_mode_authorized:
            # Echo Mode 授權時：只要在合法切換表內即可
            if current_state in legal_targets:
                return ValidationResult.LEGAL
            return ValidationResult.DRIFT_DETECTED

        # 未授權時：只允許相鄰一步合法切換
        _order = [
            ToneState.AUTHORITATIVE,
            ToneState.PROBING,
            ToneState.EMPATHETIC,
            ToneState.RESONANCE,
        ]
        prev_idx = _order.index(prev_state)
        curr_idx = _order.index(current_state)

        if abs(prev_idx - curr_idx) == 1 and current_state in legal_targets:
            return ValidationResult.LEGAL

        return ValidationResult.DRIFT_DETECTED
