"""
M4.6 -- Observer 背景萃取 Agent

實作 SPEC: docs/modules/M4_6_observer_agent_SPEC.md
研究依據: [R02 §動態狀態解碼 HMM, R10 §結構化代理工作流, R09 §6.2 BDI]
緩解風險:
  RISK-12 (萃取結果經 Eguard 過濾 PII；自動成就預設 private)
  RISK-08 (desire 經 BDI Reconciler 整合，不直接注入 Persona)
  RISK-06 (萃取結果綁定當前 role_id)
"""
