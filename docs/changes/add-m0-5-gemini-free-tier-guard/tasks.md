# Tasks:add-m0-5-gemini-free-tier-guard

**基線**:新模組,無既有 M0.5 測試;未跑後端全套 (本 change 只新增檔案,沒有既有模組 import 它)

## 1. 配額守門員

- [x] **1.1** 設定檔與載入 (`free_only` 預設、純 ASCII、`paid_capped` 驗證) — `test_default_config_is_free_only_and_ascii`、`test_config_file_override`、`test_paid_capped_requires_cap_and_prices`
- [x] **1.2** 放行 / 拒絕:mode off、未設定模型、RPM (含 share)、TPM、RPD — `test_mode_off_blocks_everything`、`test_unconfigured_model_refused`、`test_rpm_limit_respects_share`、`test_tpm_limit`、`test_rpd_exhausted_until_pacific_midnight`
- [x] **1.3** 太平洋時間日界 (PDT / PST / DST 切換日) — `test_pacific_day_start` ×4
- [x] **1.4** 429 學習與封鎖、付費偵測鎖 — `test_429_per_day_learns_limit_and_blocks_until_reset`、`test_429_per_minute_uses_retry_delay`、`test_429_input_tokens_per_minute_learns_tpm`、`test_429_without_free_tier_latches_paid_detected`、`test_unparseable_429_backs_off_60s`
- [x] **1.5** `paid_capped` 月上限 — `test_paid_capped_monthly_cap_blocks`
- [x] **1.6** SQLite 帳本持久化 + RISK-24 隔離 — `test_sqlite_ledger_persists_usage_and_learned_limits`、`test_sqlite_ledger_refuses_real_db`、`test_sqlite_ledger_rows_synthetic_and_sentinel`、`test_sqlite_ledger_refuses_foreign_db`
- [x] **1.7** 估算與 CLI — `test_plan_run_estimates_days`、`test_cli_status_and_plan`

指令:`cd services && uv run pytest ../testing/m0_5 -q`

## 2. 驗證與歸檔

- [x] **2.1** `testing/m0_5`:24 passed;`uv run ruff check m0_5_synthetic_sim ../testing/m0_5`:All checks passed
- [ ] **2.2** 後端全套 (P5) —— 未跑:測試預設會讀寫 `data/coos.db` (MVP 結案報告 §9),需使用者同意後再跑
- [x] **2.3a** Q9 拍板:共用 key,share 0.5 (設定檔預設值不變)
- [x] **2.3b** Q11:填入 AI Studio 實際限額並設 `verified = true` — `test_default_limits_match_ai_studio_and_fallback_configured` (25 passed)
- [ ] **2.4** `archive-change`

---

## 一致性分析

| 需求 (SPEC §7.4.1) | 任務 | 測試 |
| ------------------ | ---- | ---- |
| 預設只用免費額度、可設定 | 1.1 | `test_default_config_is_free_only_and_ascii` |
| RPM / TPM / RPD 守門 (RPD 太平洋午夜重置) | 1.2, 1.3 | 見上 |
| 從 429 學習實際限額 | 1.4 | `test_429_*` |
| 付費專案偵測 | 1.4 | `test_429_without_free_tier_latches_paid_detected` |
| 付費模式月上限 (可設定,非預設) | 1.5 | `test_paid_capped_monthly_cap_blocks` |
| 跨 run 保留用量與學到的限額 | 1.6 | `test_sqlite_ledger_persists_usage_and_learned_limits` |
| 估算一輪真實天數 | 1.7 | `test_plan_run_estimates_days` |

| 觸發的 RISK | 測試 |
| ----------- | ---- |
| RISK-24 | `test_sqlite_ledger_refuses_real_db`、`test_sqlite_ledger_rows_synthetic_and_sentinel`、`test_sqlite_ledger_refuses_foreign_db` |

跨 2+ 模組? 否
