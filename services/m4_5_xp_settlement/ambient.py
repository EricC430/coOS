"""
M4.5 -- Ambient XP (微量存在獎勵)

實作 SPEC: docs/modules/M4_5_xp_settlement_SPEC.md §7.2
研究依據: [R08 §六.1 IKEA] Ambient XP 額度極小，不走草稿核准流程。

[RISK-01] Ambient XP 上限 = 每日 Earned XP 的 5%；若過大，使用者不核准草稿也能拿到大量 XP，
          草稿機制形同虛設。這是分流設計的鐵律（SPEC §8 反模式）。
"""
from __future__ import annotations

from typing import Any

AMBIENT_XP_DAILY_CAP_RATIO = 0.05  # <= 每日 Earned XP 的 5%
AMBIENT_XP_LOGIN = 2  # 連續登入獎勵


def calculate_ambient_xp(daily_earned_xp: int) -> int:
    """
    計算今日可發放的 Ambient XP（不超過每日 Earned 的 5%）。

    回傳值恆 <= daily_earned_xp * 0.05。當 daily_earned=0 時回傳 0。
    """
    cap = int(daily_earned_xp * AMBIENT_XP_DAILY_CAP_RATIO)
    return min(AMBIENT_XP_LOGIN, cap)


async def grant_ambient_xp(user_id: Any, daily_earned_xp: int, gatekeeper: Any) -> int:
    """
    發放 Ambient XP（如連續登入）。

    [RISK-01] 經 calculate_ambient_xp 上限約束後才委由守門員入帳。
    回傳實際發放金額（可能為 0）。
    """
    amount = calculate_ambient_xp(daily_earned_xp)
    if amount <= 0:
        return 0
    txn = gatekeeper.settle_ambient_xp(user_id=user_id, amount=amount, reason="daily_login_streak")
    return amount if getattr(txn, "success", False) else 0
