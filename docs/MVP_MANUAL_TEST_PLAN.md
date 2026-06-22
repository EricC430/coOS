# MVP 一日典型流程八步驟 - 人工驗收測試計畫 (E2E Test Plan)

> 本文件為 `CLOSURE_REPORT_PHASE_4_5.md` 行動 B（一日典型流程八步驟）設計，旨在引導測試人員手動跑通整個系統閉環，驗證各模組（M1~M6）整合與防禦機制之正確性。

---

## 💡 測試前準備與環境配置

1. **資料庫初始化**：
   確保資料庫已執行最新遷移並有基礎專家資料：
   ```bash
   cd services
   # 確保舊專家皆已完成 PersonaCard 遷移
   uv run python migrate_experts.py
   ```
2. **啟動後端服務**：
   ```bash
   pnpm dev:backend
   ```
3. **啟動前端 Tauri 應用**：
   ```bash
   pnpm dev
   # 或直接使用過濾器啟動 tauri
   pnpm --filter @coos/desktop tauri dev
   ```

---

## 🏃 測試步驟與驗證重點

### 步驟 1：早上開機，Tauri 啟動
*   **測試目的**：驗證系統啟動時，L1 本地初始化正常，DB 自動連線。
*   **操作說明**：
    1. 點擊啟動 Tauri 應用程式。
    2. 查看後端控制台日誌。
*   **驗收準則**：
    *   Tauri 視窗正常顯示，無白屏。
    *   後端 Log 未出現 SQLite/PostgreSQL 連線失敗錯誤。
    *   `raw_tracking_logs` 有記錄到系統啟動事件（`action: system_startup`）。

---

### 步驟 2：進入角色 (Role) 儀表板
*   **測試目的**：確認全域角色上下文切換與儀表板（Heatmap/Project）顯示正常。
*   **操作說明**：
    1. 在前端 UI 左側或角色選擇器，切換至任一個活躍角色（例如：`CSIE` / `學生` 角色）。
    2. 觀察右側熱圖與今日 Project 列表。
*   **驗收準則**：
    *   熱圖（Heatmap）能正確載入歷史 XP 資料。
    *   與該角色關聯的專案（Projects）與任務卡片正確顯示。
    *   `services/m4_3_role_isolation/context.py` 的角色安全限制生效：後端僅查詢該 `role_id` 相關資料（後端 Log 顯示 GET `/api/m6_3/role_context?role_id=...`），前端 Store 中的 `expertCache` 於切換時正常清空（Flush）以防跨角色資料洩漏。

---

### 步驟 3：開啟專家聊天室，討論並觸發專案建立
*   **測試目的**：驗證 M4.2 Persona 專家對話管線、MI Selector、多氣泡延遲渲染以及 M4.6 Observer 專案偵測。
*   **操作說明**：
    1. 點選該角色下的專家（例如：微積分助教宏軒，或剛遷移的志豪）。
    2. 發送對話：「前輩，我最近想寫一個微積分的專案，打算做一個數值積分的計算器，這禮拜內會動手寫程式。」
    3. 觀察專家的回覆渲染方式與專案列表變化。
*   **驗收準則**：
    *   **人設真實度**：專家的回答包含其特色口頭禪，且符合 `PersonaCard` 的專業背景。
    *   **多氣泡延遲**：專家的長回覆會被拆分為 2~3 個訊息氣泡，且後續氣泡會延遲渲染（有一秒左右的間隔）。
    *   **專案自動萃取**：觀察對話結束後，前端儀表板的專案列表是否**自動新增了一個與「微積分/數值積分」相關的 Project 標籤**（由 M4.6 透過 SSE 廣播觸發）。

---

### 步驟 4：模擬工作遙測數據收集
*   **測試目的**：驗證遙測管線（M1.x 收集 -> M2.2 壓縮 -> M2.3 語意過濾與安全審計）。
*   **操作說明**：
    由於人工測試無法等待 2 小時，請直接使用 `curl` 模擬遙測守護行程（Telemetry Daemon）發送事件：
    ```bash
    curl -X POST http://localhost:8000/api/m1_1/event \
      -H "Content-Type: application/json" \
      -d '{
        "event_type": "keystroke",
        "role_id": "dcd6cb12-1cbe-4eab-8b7d-03d6a490f654",
        "payload": {
          "text": "import sympy as sp\ndef integrate_simpson(f, a, b, n):\n    # 撰寫辛普森數值積分器",
          "window_title": "VS Code - integrate.py"
        }
      }'
    ```
*   **驗收準則**：
    *   後端日誌顯示 `[M2.3] Semantic audit passed`。
    *   `raw_tracking_logs` 中成功寫入該遙測事件。
    *   PII 審計生效：若 `text` 包含 Email 或身分證字號，寫入 Log 的內容必須被遮蔽（顯示 `[REDACTED]`）。

---

### 步驟 5：切換狀態，觸發斷點與草稿提示
*   **測試目的**：驗證 M1.2 斷點偵測、M3.3.3 草稿生成與儀表板通知。
*   **操作說明**：
    *   **快速自動化模擬**：
        1. 模擬使用者停止寫程式並切換到娛樂網頁（如 YouTube）。使用 `curl` 發送 BREAKPOINT 事件：
           ```bash
           curl -X POST http://localhost:8000/api/m1_1/event \
             -H "Content-Type: application/json" \
             -d '{
               "event_type": "breakpoint",
               "role_id": "dcd6cb12-1cbe-4eab-8b7d-03d6a490f654",
               "payload": {
                 "reason": "focus_lost",
                 "url": "https://www.youtube.com"
               }
             }'
           ```
        2. 執行排程器產生草稿（此處手動觸發排程 API 或 Cron 方法）：
           ```bash
           # 呼叫模擬深夜排程草稿生成的端點
           curl -X POST http://localhost:8000/api/m4_4/trigger_draft_cron
           ```
    *   **專業 QA 人工測試情境 SOP (共 10 項豐富場景)**：
        為真實模擬使用者在 Windows 上的行為，請依序執行以下人工測試案例，以確保 M1.2 斷點偵測引擎在真實 OS 環境中之正確性：

        | 編號 | 測試情境 (Scenario) | 人工測試 SOP (Steps) | 預期結果 & 驗收標準 (Expected Results) |
        |---|---|---|---|
        | **1** | **標準編碼切換至娛樂網頁 (App Switch - Entertainment)** | 1. 開啟 VS Code，在程式碼檔案中持續打字 1-2 分鐘以累積專注信號。<br>2. 開啟 Chrome 瀏覽器，手動輸入網址 `https://www.youtube.com` 並開始播放任一影片。 | 1. 後端日誌應偵測到 ActivityState 改變，並記錄 `type: "app_switch"` 的斷點。<br>2. 前端 Tauri 應用應成功廣播 `BREAKPOINT_DETECTED`，使 L2 延遲通知釋放。 |
        | **2** | **編碼切換至工作相關文獻 (App Switch - Work Doc)** | 1. 在 VS Code 中持續編寫代碼 1 分鐘。<br>2. 切換至 Chrome 瀏覽器並開啟 StackOverflow (`https://stackoverflow.com`) 或 Python 官方文件 (`https://docs.python.org`) 查詢語法。 | 1. 雖然偵測到視窗切換，但因 URL 屬於允許的「工作組(Work Group)」，故**不**會觸發任何斷點。<br>2. L2 通知應繼續留在隊列中，不會打擾開發者。 |
        | **3** | **長時間無活動閒置斷點 (Idle Timeout)** | 1. 在 VS Code 中進行若干代碼輸入。<br>2. 停止敲擊鍵盤，且不移動滑鼠，將電腦完全靜置 5 分鐘。 | 1. 靜置滿 5 分鐘後，後端自動觸發 `type: "idle_timeout"` 斷點。<br>2. 儀表板成功接收事件，日報草稿通知亮起。 |
        | **4** | **高速編碼突然停頓卡住 (WPM Drop)** | 1. 在 VS Code 中高速打字（WPM > 40）持續 1 分鐘。<br>2. 突然放慢打字速度（如 10 秒敲 1 個字元），但視窗焦點仍維持在 VS Code。 | 1. 在 30 秒內 WPM 下滑 > 50% 時，觸發 `type: "wpm_drop"` 斷點。<br>2. 驗證在沒有切換視窗的情況下，僅靠輸入流變化也能精準觸發斷點。 |
        | **5** | **VS Code 焦點移出 (IDE Focus Leave)** | 1. 在 VS Code 編輯器中進行程式撰寫。<br>2. 用滑鼠點擊 Windows 工作列上的「檔案總管」或點擊 Windows 桌面空白處，讓 VS Code 失去焦點。 | 1. M1.3.1 擴充功能偵測到焦點離開，並拋出 `ide_focus_leave` 事件。<br>2. 斷點引擎將此視為 `BreakpointType::IDE_FOCUS_LEAVE`，成功將焦點移出列為斷點。 |
        | **6** | **斷點冷卻防禦功能 (Cooldown Gating)** | 1. 執行「情境 1」切換至 YouTube 並觸發第一個斷點。<br>2. 立即切換回 VS Code 打字 10 秒，再次切換至 Netflix 網頁。 | 1. 由於冷卻時間限制（5 分鐘），第二次切換在 5 分鐘內**不**會再發送新的 `BREAKPOINT_DETECTED` 事件。<br>2. 防止頻繁來回切換視窗造成通知轟炸。 |
        | **7** | **多 AI 專家通知錯開釋放 (Staggered Dispatcher)** | 1. 在後端暫存區手動排隊 3 個不同專家的 L2 通知。<br>2. 在 VS Code 編碼後切換至娛樂網頁觸發斷點。 | 1. 3 個通知應以隨機延遲（1~60秒）依序彈出，不得在同一秒內全部顯示。<br>2. 觀察後端 Log 是否顯示 `StaggeredNotificationDispatcher` 計算出的延遲秒數。 |
        | **8** | **錯開釋放期間重回深度工作 (Re-entry Block)** | 1. 與「情境 7」相同，排隊 3 個通知並觸發斷點。<br>2. 在第一個通知彈出後，立刻切換回 VS Code 開始高速編碼。 | 1. 系統檢測到狀態重回 `DEEP_WORK`。<br>2. 錯開釋放調度器應立即**暫停**後續未發送的通知，將其留至下一個斷點。 |
        | **9** | **深度工作 Windows 全域靜音與恢復 (System Mute)** | 1. 在 `user_consents` 中確保已授權系統通知控制權。<br>2. 持續編碼 10 分鐘進入 `DEEP_WORK` 狀態。<br>3. 切換至娛樂網頁（觸發斷點）。 | 1. 進入 `DEEP_WORK` 時，Windows 通知模式（Focus Assist）應被設定為「請勿打擾/靜音」模式。<br>2. 觸發斷點時，應**立即恢復**正常的 Windows 通知模式。 |
        | **10** | **守護行程斷線之降級防禦 (Degraded Mode)** | 1. 手動關閉 Telemetry Daemon 或停止其 Heartbeat 發送。<br>2. 等待 10 秒以上（Heartbeat 超時），並生成一筆 L2 通知。 | 1. 斷點引擎日誌應發出 WARN，並自動進入 `degraded` 降級模式。<br>2. L2 通知應**不經過斷點門控**直接發送，確保在背景服務異常時通知仍可達。 |
        | **11** | **Doom Scrolling 狀態偵測 (Doom Scrolling)** | 1. 開啟瀏覽器並切換至娛樂/社交網頁（例如 YouTube、Bilibili 或 Facebook）。<br>2. 持續頻繁地向下滾動頁面（每分鐘捲動 > 30 次），且每次更換頁面或點擊不同影片（使平均頁面停留時間 < 15 秒），持續進行 5 分鐘。 | 1. 後端 `focus_session_ended` 事件的 payload 應成功將該專注時段判定為 `activity_state: "DOOM_SCROLLING"`。<br>2. 驗證滑鼠滾動與頁面停留的多信號融合分類功能運作正常。 |

*   **驗收準則**：
    *   前端儀表板右上角或日報模組會亮起「草稿待審核」的紅色徽章或通知（M3.9）。
    *   所有的斷點事件皆正確記錄至 `raw_tracking_logs` 中（M0.4）。


---

### 步驟 6：點開日報草稿並進行核准
*   **測試目的**：驗證 M3.3.3 互動式表單與核准流程。
*   **操作說明**：
    1. 點開待核准的日報草稿。
    2. 查看 AI 描述的客觀數據（例如：「本日在 VS Code 撰寫微積分辛普森積分器 2.0 小時，隨後切換至 YouTube」）。
    3. 在「主觀回顧」輸入框填入：「今天辛普森積分公式邏輯理順了，效能還不錯。」
    4. 點擊「確認並核准（Approve）」。
*   **驗收準則**：
    *   點擊核准後，草稿狀態變更為 `is_reviewed = 1`。
    *   草稿卡片從待辦清單中移除。

---

### 步驟 7：XP 發放結算與收藏品獎勵
*   **測試目的**：驗證 M4.5 XP 結算引擎（ACID 守門員）與 M3.5 獎勵系統。
*   **操作說明**：
    1. 前端或背景會自動呼叫發放 API（`/api/m4_5/grant_xp`）。
    2. 切換到「個人收藏/徽章」或「首頁儀表板」。
*   **驗收準則**：
    *   使用者的全域 XP 增加（例如增加 100 XP）。
    *   後端 Log 顯示 `[M4.5] XP successfully granted for reviewed draft`。
    *   若嘗試對同一個已發放的草稿再次呼叫 `/api/m4_5/grant_xp`，系統應報錯並拒絕（ACID 冪等性防禦）。

---

### 步驟 8：本地隱私核對（No PII to Cloud）
*   **測試目的**：確認所有遙測原始數據與對話日誌僅落地 L1 SQLite，未發送至雲端。
*   **操作說明**：
    1. 打開 `raw_tracking_logs` 表或本地日誌檔案。
    2. 檢查是否有任何敏感 PII。
*   **驗收準則**：
    *   Gemini API 呼叫的日誌（W8 格式）雖包含對話，但已通過 `eguard.mask_pii()` 去識別化。
    *   工作按鍵原始歷程（Keystroke raw text）僅存放於本地 SQLite，未出現在任何外發的 API payload 中。

---

## 📝 測試結果與影片備忘錄

測試完成後，請將錄製的 E2E 流程影片（`*.webp` / `*.mp4`）與截圖儲存至：
*   `C:\Users\chent\.gemini\antigravity\brain\28c5c9db-f4b6-4c0d-a318-f3d744e9b7f3\artifacts\`

並在 [walkthrough.md](file:///C:/Users/chent/.gemini/antigravity/brain/28c5c9db-f4b6-4c0d-a318-f3d744e9b7f3/walkthrough.md) 中更新驗證結果。
