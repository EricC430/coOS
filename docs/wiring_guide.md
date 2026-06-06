# coOS 模組串接開發文件 (Module Wiring Development Guide)

本文件說明 coOS 系統中，如何將 FastAPI 網關（Gateway）的模擬（Mock）端點正式串接至後端 LangGraph 引擎、Gemini 2.0 狀態機、資料庫配接器（Database Adapters）與 XP 結算守門員等真實業務邏輯。

---

## 1. 架構設計與安全邊界

coOS 採用雙層（L1 本地/L3 雲端）資料架構，為確保多角色沙盒隔離（Role Sandboxing）與資訊安全，系統在串接層設計了兩大核心機制：

### 1.1 `RoleIsolationMiddleware` (角色隔離中介軟體)
*   **路由過濾**：僅攔截以 `/api/m4_` 與 `/api/m6_` 開頭的端點，確保系統遙測接收點（如 `/api/m1_1/event`）不因缺少 `X-Role-ID` 標頭而被阻擋。
*   **線程沙盒**：強行校驗 `X-Role-ID` 的歸屬關係，並在 LangGraph 執行時，將 Thread ID 強制加上 `role_id::` 前綴（例如 `role_id::thread_uuid`），防止不同角色間的對話上下文與狀態交叉污染。

### 1.2 `AsyncDBAdapter` (非同步資料庫配接器)
*   **動態分流**：根據 SQL 查詢目標表格自動判定。
    *   **L1 本地表**（如 `role_implicit_states`, `chat_transcripts` 等）強制路由至本地 SQLite 檔案。
    *   **L3 雲端表**（如 `ai_experts`, `role_projects`, `goals`, `promises` 等）路由至雲端 PostgreSQL (Supabase)。
*   **優雅降級 (Graceful Degradation)**：當雲端 PostgreSQL 未設定或連線失敗時，系統會自動切換為本機預設的 Expert 與 Project 模擬資料，確保離線開發與演示流程不中斷。

---

## 2. 核心端點串接說明

### 2.1 對話與專家配對端點 (M4.1 & M4.2)
*   **接口**：`/api/m4_1/chat` 及 `/api/m4_1/match_persona`
*   **串接邏輯**：
    1. 接收使用者訊息後，調用 `build_role_context` 載入當前角色脈絡。
    2. 調用本地 Gemma 邊緣管道（M2.2）將明文壓縮成去識別化的 **Intent Vector**（隱私防護 L2 層）。
    3. 執行 LangGraph 頂層協作圖 `get_router_graph()`。
    4. 在 `invoke_persona_node` 節點中，實時調用角色狀態機 `get_persona_graph()`，並調用 Gemini 2.0 取得 Persona 回應。
    5. 通過 `DriftShield` 注入檢測後，將對話紀錄寫入本地 SQLite 的 `chat_transcripts` 表。

### 2.2 角色上下文 Context 端點 (M6.3)
*   **接口**：`/api/m6_3/role_context`
*   **串接邏輯**：
    1. 調用 `build_role_context` 組裝 **Project (專案)**、**Role (角色)**、**Promises (承諾)** 與 **Goal (專家目標)** 四槽位資料。
    2. 依據前端 DTO 結構進行格式化輸出，若資料庫為空則提供預設的學業引導目標。

### 2.3 日報與反思編輯端點 (M6.4)
*   **接口**：`/api/m6_4/daily_timeline` 及 `/api/m6_4/reflections/{reflection_id}` (PATCH)
*   **串接邏輯**：
    1. `daily_timeline` 藉由聯表查詢 PostgreSQL 的 `daily_reflections` 與 `daily_reflection_segments`。
    2. 編輯反思端點執行 **微摩擦力 (Micro-friction)** 驗證：強制校驗 `user_feeling` 與 `user_action_plan` 不得為空白字元，防止用戶刷分。
    3. 核准日報（`is_reviewed=true`）時，將日報草稿狀態變更為 `is_draft=False`。

### 2.4 XP 發放端點 (M4.5 & M6.5)
*   **接口**：`/api/m4_5/grant_xp` (PATCH)
*   **串接邏輯**：
    1. 強制執行 **[RISK-01] 三重守門**：校驗日報必須為已審核（`is_reviewed=True`）、有感受（`user_feeling` 非空）、有行動方案（`user_action_plan` 非空）。
    2. 調用 `m4_5_xp_settlement` 計算實得 Earned XP。
    3. 委由 `XPGatekeeper` 發起 **ACID 原子交易**，同步更新使用者現有 XP (`current_xp`)、終身累計 XP (`lifetime_xp`)，標記反思已結算，並寫入 `xp_ledger` 變動日誌。

### 2.5 鍵盤輸入速率監聽 (M1.1.2)
*   **職責與串接**：
    1. 實作 Rust 遙測守護行程（`m1_1_telemetry_daemon`）中的 `InputDebouncer` 衍生 `Clone` 特徵，供跨線程共享。
    2. 在守護行程啟動時，調用 `spawn_raw_input_listener` 拉起專屬的背景 Win32 訊息循環（Message Loop）執行緒。
    3. 註冊帶有 `WS_EX_TOOLWINDOW` 樣式的隱藏視窗（不會顯示於任務列與 Alt-Tab），並註冊 `RAWINPUTDEVICE` 監聽鍵盤裝置（`usUsagePage = 1`, `usUsage = 6`）並指定 `RIDEV_INPUTSINK` 旗標以開啟後台非焦點捕獲。
    4. 當使用者在 OS 中打字，系統訊息泵將發送 `WM_INPUT` 至隱藏視窗。程式過濾 `WM_KEYDOWN` 與 `WM_SYSKEYDOWN` 事件後，原子累加次數至 `debouncer.on_key_event()`。
    5. 用於每 5 秒發送 `keystroke_burst` 到 API 網關與計算 focus session 結束時的平均打字速度（WPM）。

### 2.6 偏好與隱私設定端點 (Settings & Consent)
*   **接口**：`/api/settings` (GET / POST)
*   **串接邏輯**：
    1. **GET `/api/settings?role_id=xxx`**：
       - 從 L1 本地表 `user_consents` 讀取使用者的隱私授權狀態（如：是否同意遙測採集 `content_capture`、是否同意語音雲端推論 `voice_cloud`、是否啟用雲端同步 `cloud_sync`）。
       - 從 `role_settings` 讀取當前角色的偏好設定（包含風格主題 `theme`、通知開關 `notification_enabled`、日報生成時間 `daily_report_time` 與專注時間 `focus_hours_start` 至 `focus_hours_end`）。
       - 讀取當前 sidecar 的 `.env` 快取以取得邊緣 AI 配置（如 Ollama 位址 `ai_local_host`、Gemma 模型名稱 `gemma_model`、iPad 推理位址 `ipad_ai_local_host`）。
    2. **POST `/api/settings?role_id=xxx`**：
       - 接受 Pydantic 模型的 Payload。
       - 清除並寫入新的 consent 至 SQLite `user_consents` 表。
       - 寫入或更新角色設定至 `role_settings` 表。
       - 在記憶體中熱更新 `Settings` 單例，並透過檔案系統寫入持久化回根目錄下的 `.env` 檔案中。

---

## 3. 測試與驗證指南

完成串接後，請確保所有單元測試能正常運行：

### 3.1 執行本地單元測試
在專案根目錄下，使用 `pytest` 執行路由、角色與結算測試：
```bash
python -m pytest testing/m4_1 testing/m4_2 testing/m4_5 testing/m4_3
```

### 3.2 驗證手冊 (Manual Verification)
1. 啟動 FastAPI 服務：
   ```bash
   poetry run uvicorn services.main:app --reload
   ```
2. 使用 Postman 或 curl 測試對話端點，確認其非硬編碼回覆：
   ```bash
   curl -X POST http://127.0.0.1:8000/api/m4_1/chat \
     -H "Content-Type: application/json" \
     -H "X-Role-ID: csie_001" \
     -d '{"content": "微積分好難", "thread_id": "test_thread"}'
   ```
3. 確認回應中包含配對的 Persona ID (`robert_001`) 與流暢的學長口吻回覆。

### 3.3 執行 Rust 遙測守護行程單元與整合測試
在專案根目錄下，建置守護程序並執行 Rust 單元測試：
```bash
cargo build -p m1_1_telemetry_daemon
cargo test -p m1_1_telemetry_daemon
```
執行 OS 遙測的 Python 整合測試（請於 `services/` 目錄下調用虛擬環境）：
```bash
cd services
.venv\Scripts\pytest.exe ..\testing\m1_1
```
