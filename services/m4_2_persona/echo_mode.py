"""
M4.2.2 -- Echo Mode 阻抗消解控制器

SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md §7.2
Research: [R03: Echo Mode §3.2] 5 步漸進切換原則
Risk: RISK-02 (Echo Mode 切換不觸發 ARPM 還原)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToneState(StrEnum):
    """[R03 §3.2] Persona 音調狀態，對應 Agency 值域。"""
    AUTHORITATIVE = "authoritative"  # Agency 0.80-0.90
    PROBING = "probing"              # Agency 0.55-0.70
    EMPATHETIC = "empathetic"        # Agency 0.20-0.40
    RESONANCE = "resonance"          # Agency 0.10-0.20


# Agency 各狀態中點值
_AGENCY_MID: dict[ToneState, float] = {
    ToneState.AUTHORITATIVE: 0.85,
    ToneState.PROBING: 0.625,
    ToneState.EMPATHETIC: 0.30,
    ToneState.RESONANCE: 0.15,
}

# [R03 §3.2] 合法切換空間 — ARPM 必須認得此表
LEGAL_TRANSITIONS: dict[ToneState, list[ToneState]] = {
    ToneState.AUTHORITATIVE: [ToneState.PROBING, ToneState.EMPATHETIC],
    ToneState.PROBING: [ToneState.AUTHORITATIVE, ToneState.EMPATHETIC],
    ToneState.EMPATHETIC: [ToneState.RESONANCE, ToneState.PROBING],
    ToneState.RESONANCE: [ToneState.EMPATHETIC],  # 不可直接跳回權威
}


class IllegalToneTransition(Exception):
    pass


@dataclass
class TransitionPlan:
    """5 步漸進切換計畫。"""
    steps: list[float]

    @property
    def steps_remaining(self) -> int:
        return len(self.steps)


@dataclass
class EchoModeResult:
    """process() 的回傳結果。"""
    target_agency: float
    transition_plan: TransitionPlan
    triggered: bool = True


class EchoModeController:
    """
    [R03: Echo Mode §3.2] 動態音調控制器。

    偵測阻抗後，規劃 5 步漸進 Agency 切換，
    確保 ARPM 不將其誤判為人設漂移 (RISK-02)。
    """

    TRANSITION_STEPS = 5

    def __init__(self, current_state: ToneState = ToneState.AUTHORITATIVE):
        self.current_state = current_state

    def plan_transition(self, from_state: ToneState, to_state: ToneState) -> TransitionPlan:
        """
        [R03 §3.2] 規劃 5 步線性漸進切換計畫。
        非法切換拋出 IllegalToneTransition。
        """
        if to_state not in LEGAL_TRANSITIONS.get(from_state, []):
            raise IllegalToneTransition(
                f"{from_state} → {to_state} 非合法切換路徑"
            )
        start = _AGENCY_MID[from_state]
        end = _AGENCY_MID[to_state]
        steps = [
            start + (end - start) * i / self.TRANSITION_STEPS
            for i in range(1, self.TRANSITION_STEPS + 1)
        ]
        return TransitionPlan(steps=steps)

    def process(self, user_msg: str, current_agency: float) -> EchoModeResult:
        """
        [R03 §3.2] 根據阻抗偵測結果決定是否啟動漸進切換。

        偵測到防衛語氣時，Agency 漸進下降至下一合法狀態，
        不可一步跳到最低點 (RISK-02)。
        """
        from .reactance import rule_based_reactance
        score = rule_based_reactance(user_msg)

        if score.score < 0.3:
            # 無阻抗：維持當前狀態
            return EchoModeResult(
                target_agency=current_agency,
                transition_plan=TransitionPlan(steps=[current_agency] * self.TRANSITION_STEPS),
                triggered=False,
            )

        # 決定目標狀態（往下一合法狀態移動）
        target_state = self._next_lower_state(self.current_state)
        plan = self.plan_transition(self.current_state, target_state)
        # 第一步的 agency 即為本次回傳的 target_agency
        return EchoModeResult(
            target_agency=plan.steps[0],
            transition_plan=plan,
            triggered=True,
        )

    def _next_lower_state(self, state: ToneState) -> ToneState:
        """回傳下一個 Agency 較低的合法狀態。"""
        order = [
            ToneState.AUTHORITATIVE,
            ToneState.PROBING,
            ToneState.EMPATHETIC,
            ToneState.RESONANCE,
        ]
        idx = order.index(state)
        if idx + 1 < len(order):
            # 確認下一狀態是合法切換目標
            next_state = order[idx + 1]
            if next_state in LEGAL_TRANSITIONS.get(state, []):
                return next_state
        return state  # 已是最低，維持
