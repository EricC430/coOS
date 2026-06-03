"""
M4.4 -- 吉布斯反思結構模板

實作 SPEC: docs/modules/M4_4_natural_elicitation_draft_SPEC.md §7.4
研究依據: [R08 §六.2 吉布斯循環 + R10 §MindScape 反思鷹架]

[RISK-15] 草稿 ai_description 只可使用泛化指標 (app_bucket / duration_minutes)，
          結構上完全不讀取 content_summary / window_title，從根本杜絕側通道洩漏。
[R08 §五] ai_analysis 只填客觀數據與初步觀察，主觀感受與行動計畫留給使用者 (微摩擦力)。
"""
from __future__ import annotations

from typing import Any

# [RISK-15] 允許進入草稿的泛化欄位白名單。content_summary / window_title 永不在內。
_ALLOWED_PAYLOAD_KEYS = {"app_bucket", "duration_minutes", "wpm_avg"}


def _payload(log: Any) -> dict:
    """取 log 的 payload dict（支援 dataclass/SimpleNamespace/dict）。"""
    if isinstance(log, dict):
        return log.get("payload", log)
    return getattr(log, "payload", {}) or {}


def build_gibbs_description(logs: list, elicited: list) -> str:
    """
    吉布斯階段 1: 客觀描述 (AI 填寫)。

    [RISK-15] 只讀 _ALLOWED_PAYLOAD_KEYS 內的泛化指標，禁用 content_summary。
    """
    segments: list[str] = []
    for log in logs:
        p = _payload(log)
        bucket = p.get("app_bucket", "unknown")
        duration = p.get("duration_minutes", 0)
        segments.append(f"在「{bucket}」類型活動上花費約 {duration} 分鐘")

    # 加入套問取得的自報耗時（M4.4.1+M4.4.2 白天收集）。
    for e in elicited:
        project = e.get("project") if isinstance(e, dict) else getattr(e, "project", "")
        minutes = e.get("duration_minutes") if isinstance(e, dict) else getattr(e, "minutes", 0)
        segments.append(f"自述「{project}」花費約 {minutes} 分鐘")

    if not segments:
        return "今日無可供描述的活動紀錄。"
    return "；".join(segments) + "。"


def build_gibbs_analysis(logs: list, elicited: list) -> str:
    """
    吉布斯階段 2: 初步分析 (AI 填寫)。

    [R08 §五] 不填主觀感受，明確將「感受」與「行動」留給使用者親自填寫。
    """
    total_mins = sum(_payload(log).get("duration_minutes", 0) for log in logs)
    for e in elicited:
        if isinstance(e, dict):
            total_mins += e.get("duration_minutes", 0)
        else:
            total_mins += getattr(e, "minutes", 0)
    return f"全日活躍約 {total_mins} 分鐘。（主觀感受與行動計畫請您親自填寫）"
