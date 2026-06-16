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
*   **驗收準則**：
    *   前端儀表板右上角或日報模組會亮起「草稿待審核」的紅色徽章或通知（M3.9）。

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
