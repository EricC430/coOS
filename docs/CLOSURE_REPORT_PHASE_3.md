# Phase 3 Closure Report

**完成日期**：2026-06-03
**狀態**：✅ 完成閉環
**測試通過率**：202 Python passed + 13 TS (M1.3.1 Vitest) + 15 JS (M1.3.2 Vitest)

---

## 1. 完成的模組清單 (5/5 MVP)

| 模組 | 職責 | 狀態 | 測試 | 引用 |
|------|------|------|------|------|
| **M1.4** | Git 與工作流遙測（Webhook + 本地 Git 掃描） | ✅ | 14/14 | [R06 §2.1, R02 §1.2] |
| **M1.1** | OS 遙測守護行程（Rust sidecar） | ✅ | 15 Rust + 15 Python | [R02 §1, R06 §2.1] |
| **M1.2** | 斷點偵測引擎（Python 狀態機） | ✅ | 22/22 | [R08 §二/三/一, RISK-04] |
| **M1.3.1** | VS Code Extension（Shannon Entropy + 人機協作） | ✅ | 13 TS + 7 Python | [R02 §1.1/1.2] |
| **M1.3.2** | 瀏覽器擴充（domain bucketing + dwell time） | ✅ | 15 JS + 8 Python | [R06 §2.1, R02 §1.2, RISK-15] |

**累計測試**（含 Phase 1、2 回歸）：202 Python passed

---

## 2. 架構決定（本 Phase 拍板）

| 決定 | 選項 | 理由 |
|------|------|------|
| M1.1 crate 位置 | 獨立 `services/m1_1_telemetry_daemon/` | sidecar 模式，與 Tauri 分離，watchdog 邏輯清晰 |
| M1.2 語言 | Python（FastAPI sidecar） | 狀態機邏輯在 Python；Windows 通知靜音透過 IPC 委託 Tauri Rust |
| M1.4 Webhook 連通 | `gh webhook forward`（取代 Cloudflare Tunnel） | MVP 階段零基礎設施成本；Cloudflare 方案保留 Phase 6+ |
| Cargo workspace | 根目錄 `Cargo.toml`，含 `src-tauri` + `m1_1_telemetry_daemon` | 統一 profile.release 設定 |

---

## 3. Phase Closure 驗收

**驗收方式**：手動執行

```
1. uvicorn main:app --port 8000
2. cargo run -p m1_1_telemetry_daemon
3. 在任意視窗操作數分鐘
4. 切換到瀏覽器
```

**確認項目**：
- ✅ `raw_tracking_logs` 出現 `M1.1.1 window_changed` 事件
- ✅ `raw_tracking_logs` 出現 `M1.1.3 focus_session_ended` 事件
- ✅ `raw_tracking_logs` 出現 `M1.1.3 daemon_heartbeat` 事件（每 30 秒）
- ✅ `raw_tracking_logs` 出現 `M1.2 breakpoint_detected` 事件（切換 app 觸發）
- ✅ DB Browser for SQLite 可在 `data/coos.db` 正常瀏覽所有事件

---

## 4. 修正的 Bug（Phase 3 期間發現）

| 問題 | 原因 | 修正 |
|------|------|------|
| `raw_tracking_logs` 空白 | `AsyncLogWriter.start()` 未在 lifespan 呼叫，事件進 queue 但不寫磁碟 | lifespan 加入 `await _log_writer.start()` / `stop()` |
| M1.1 事件沒有 feed M1.2 | `/api/m1_1/event` 只寫 raw_tracking_logs，未轉發 BreakpointEngine | 端點同時呼叫 `engine.feed()` |
| Rust 3 個 warning | 未使用 import / variable | 移除 `GetCurrentProcessId`，`AppBucket`，加 `_key_count` 前綴 |
| `profile.release` 在 leaf crate | Cargo workspace 要求 profile 在 root | 移至根目錄 `Cargo.toml` |

---

## 5. 技術債

| 項目 | 原因 | 優先級 | 目標 |
|------|------|--------|------|
| **M1.1.2 WPM = 0** | Raw Input hook（`RegisterRawInputDevices` + `WM_INPUT`）未接。需要 dedicated OS thread 跑 Win32 message loop，與 Tokio async 架構需橋接，超出 Phase 3 範圍 | **P1** | **Phase 4 開始前**（M4.8 隱性狀態推論正式消費 WPM 時） |
| M1.1.2 mouse_clicks = 0 | 同上，Raw Input 滑鼠事件未接 | P2 | Phase 5 |
| `m6_2_postgresql/models.py` Pydantic `ne=` 警告 | `Field(ne=0)` deprecated in Pydantic v2 | P3 | Phase 4+ |
| M1.3.1 `.vsix` 打包與自動安裝 | 目前只有原始碼，未用 `vsce package` 打包；Tauri 自動安裝邏輯未實作 | P2 | Phase 5（UI 整合）|
| M1.3.2 Native Messaging Host 安裝 | `coos_native_host` Windows Registry 寫入未自動化 | P2 | Phase 5（安裝程式）|
| M1.3.2 Firefox `background.scripts` 相容 | Firefox 不完全支援 ES Module Service Worker，需 fallback | P3 | Phase 5 |

---

## 6. 整合風險驗證

| 風險 | 組合 | 狀態 |
|------|------|------|
| RISK-04 | M1.2 + M3 XP 慶祝動畫 | ✅ L1/L2/L3 門控邏輯實作；M3 Phase 5 再做端對端驗收 |
| RISK-15 | M1.1 content_summary + M4.4 草稿 + M6.2 雲端 | ✅ CaptureMode::Off 預設；M0.4 拒絕 browsing_content/raw_code 鍵 |

---

## 7. Lint & CI 狀態

- ✅ `ruff check` 全綠（Python 新代碼：`m1_2_breakpoint/`, `m1_4_github/`）
- ✅ `cargo build -p m1_1_telemetry_daemon` 零 warning、零 error
- ✅ `vitest run` 全綠（M1.3.1 TS 13/13、M1.3.2 JS 15/15）
- ✅ `pytest` 202 passed（含 Phase 1、2 回歸）

---

## 8. git 提交歷史（本 Phase）

```
6efb425 fix(M1.1→M1.2): wire /api/m1_1/event to BreakpointEngine
8c02618 fix(M0.4): start AsyncLogWriter in lifespan
3a05a1f fix(M1.1): remove unused imports/variable, move profile.release to workspace root
c5bc165 feat(M1.3.2): Browser Extension — tab focus & reading behavior telemetry
95bb909 feat(M1.3.1): VS Code Extension — code activity telemetry sensor
2a42fbe feat(M1.2): Defer-to-Breakpoint Engine — state machine + notification gate
315dfd6 feat(M1.1): OS Telemetry Daemon — Rust sidecar + FastAPI ingest endpoint
d31e787 feat(M1.4): Git & Workflow Telemetry — Webhook + Local Git Monitor
```

---

## 結語

**Phase 3 成功完成**。端側感知管線全部接通：

- M1.1 Rust 守護行程在 OS 層採集焦點/視窗事件，寫入 `raw_tracking_logs`
- M1.2 Python 引擎消費 M1.1 事件流，在自然斷點派發 `BREAKPOINT_DETECTED`
- M1.3.1/M1.3.2 從 IDE 和瀏覽器補充行為訊號
- M1.4 雙軌感知 Git 活動（本地 + Webhook）

**唯一待修的 P1 技術債**：M1.1.2 WPM Raw Input hook，Phase 4 開始前補齊，屆時 M4.8 隱性狀態推論才能正確消費 WPM 作為認知狀態特徵。

**下一步**：Phase 4 — Agent 邏輯核心（M4.1 LangGraph Router + M4.2 Persona + M4.3~M4.7）。

---

**簽名**：Claude Code (Sonnet 4.6)
**驗證方式**：
```bash
cd services && .venv/Scripts/pytest.exe ../testing/ --ignore=../testing/local_llm --ignore=../testing/m0_2 -q
# 結果：202 passed
```
