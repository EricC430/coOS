"""
M4.5.1 -- XP 結算守門員 (XP Settlement Gate)

實作 SPEC: docs/modules/M4_5_xp_settlement_SPEC.md §7.1
研究依據: [R08 §六.1 IKEA 效應 + R08 §四.2 微摩擦力]

[RISK-01] 三重守門：is_reviewed=True AND user_feeling 非空 AND user_action_plan 非空。
          三者缺一即拒絕，絕不在草稿狀態發放 Earned XP（CLAUDE.md 鐵律第 6 條）。
[RISK-14] 實際 current_xp / lifetime_xp 異動委由 M6.5 XPGatekeeper 原子完成。

設計：本引擎只負責「計算金額」與「呼叫守門員」；不直接寫 DB。XP 計算公式參數見 SPEC §9。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SettlementResult:
    granted: bool
    amount: int = 0
    reason: str = ""


# ── XP 計算公式參數 (SPEC §9 決議) ─────────────────────────────────────────
BASE_XP_PER_HOUR = 25  # 每小時基礎 XP
GOAL_ALIGNMENT_MULTIPLIER = 1.5  # 對齊專家目標的加成倍率
LEARNING_NOTE_BONUS = 10  # 填寫 user_learned 的固定紅利
MIN_PARTICIPATION_XP = 5  # 最低參與獎勵（防止 0/負值）

# 深思熟慮加成 (Reflection Duration Bonus)
MIN_REFLECTION_SECS = 15  # 觸發加成的最少秒數
MAX_REFLECTION_SECS = 300  # 計算加成的上限秒數（防掛機刷分）
DURATION_XP_RATE = 0.1  # 每秒給予的 XP


def compute_earned_xp(reflection: Any, approval_duration_seconds: float = 0) -> int:
    """
    純函式：依 SPEC §9 公式計算應得 Earned XP。

    基礎 = (activity_minutes / 60) * 25
    目標對齊 -> *1.5
    user_learned 非空 -> +10
    核准停留 >= 15s -> +min(秒數,300)*0.1
    取整後最低 5。
    """
    hours = (getattr(reflection, "activity_minutes", 0) or 0) / 60
    base_xp = hours * BASE_XP_PER_HOUR

    is_aligned = getattr(reflection, "goal_aligned", False)
    calculated = base_xp * (GOAL_ALIGNMENT_MULTIPLIER if is_aligned else 1.0)

    learned = getattr(reflection, "user_learned", None)
    if learned and learned.strip():
        calculated += LEARNING_NOTE_BONUS

    if approval_duration_seconds >= MIN_REFLECTION_SECS:
        clamped = min(approval_duration_seconds, MAX_REFLECTION_SECS)
        calculated += int(clamped * DURATION_XP_RATE)

    return max(int(calculated), MIN_PARTICIPATION_XP)


async def settle(
    reflection: Any,
    user: Any,
    gatekeeper: Any,
    approval_duration_seconds: float = 0,
) -> SettlementResult:
    """
    [RISK-01] 三重守門 + 冪等性檢查，通過後委由守門員原子發放。

    回傳 SettlementResult；實際 XP 異動由 gatekeeper.settle_earned_xp 完成。
    """
    # Guard 1: 草稿不結算 [RISK-01]
    if getattr(reflection, "is_draft", True) or not getattr(reflection, "is_reviewed", False):
        return SettlementResult(False, reason="draft_not_approved")

    # Guard 2: 微摩擦力欄位必填 [R08 §四.2]
    feeling = getattr(reflection, "user_feeling", None)
    if not feeling or not feeling.strip():
        return SettlementResult(False, reason="missing_user_feeling")
    action_plan = getattr(reflection, "user_action_plan", None)
    if not action_plan or not action_plan.strip():
        return SettlementResult(False, reason="missing_user_action_plan")

    # Guard 3: 冪等性 — 已結算不重複發放
    if getattr(reflection, "xp_settled", False):
        return SettlementResult(False, reason="already_settled")

    earned_xp = compute_earned_xp(reflection, approval_duration_seconds)
    if earned_xp <= 0:  # 防禦：理論上 compute 已保證 >= MIN_PARTICIPATION_XP
        rid = getattr(reflection, "id", "?")
        logger.warning("[M4.5] negative_xp_calculation reflection=%s", rid)
        return SettlementResult(False, reason="negative_xp_calculation")

    # [RISK-14] 原子交易：xp_ledger + users(current_xp+lifetime_xp) + reflection.xp_settled
    txn = gatekeeper.settle_earned_xp(
        reflection_id=reflection.id,
        user_id=user.id,
        amount=earned_xp,
    )
    if not txn.success:
        # SPEC §7.4: 交易失敗 -> 靜默重試（由排程重試佇列處理），此處回報未發放。
        return SettlementResult(False, reason=txn.error_reason or "settlement_failed")

    return SettlementResult(True, amount=earned_xp, reason="approved")


def deduct_xp(user: Any, amount: int) -> None:
    """
    [RISK-14] 消費 XP：只減 current_xp，lifetime_xp 唯增不減。

    用於非守門員路徑的本地預扣顯示；正式扣款仍走 XPGatekeeper.stake_xp / deduct_xp_for_gacha。
    """
    user.current_xp -= amount
    # lifetime_xp 不動 [RISK-14]
