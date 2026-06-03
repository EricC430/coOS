"""
M4.5 -- 零摩擦 XP 自動結算引擎 (Zero-Friction XP Settlement Engine)

實作 SPEC: docs/modules/M4_5_xp_settlement_SPEC.md
研究依據: [R08 §六.1 IKEA 效應, R08 §五 意圖脫鉤, R08 §四.2 微摩擦力]
緩解風險:
  RISK-01 (is_reviewed + user_feeling + user_action_plan 三重守門)
  RISK-14 (current_xp 與 lifetime_xp 原子同步；lifetime 唯增不減)
  RISK-13 (已結算反思不自動回滾)
"""
