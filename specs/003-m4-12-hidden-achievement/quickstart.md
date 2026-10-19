# Quickstart & E2E Validation: M4.12 隱藏成就驗證引擎

**Branch**: `003-m4-12-hidden-achievement` | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

本文件提供開發者與測試人員端到端執行、驗證 M4.12 隱藏成就驗證引擎之指南。

---

## 1. 前置準備 (Prerequisites)

- Python 3.11+ 虛擬環境啟動
- 安裝依賴：`pip install -r services/requirements.txt`（包含 FastAPI, SQLAlchemy, WebSockets, Pytest, Pytest-Asyncio）
- 本地測試資料庫：支援 SQLite 記憶體資料庫或本地 `coos.db`

---

## 2. 自動化測試驗證 (Automated Verification)

執行專屬測試套件驗證五大關鍵面向：

```bash
# 1. 驗證 M3.11.3 絕對無 UI 狀態與 API 0% 洩漏（防 FOMO）
pytest testing/m4_12/test_zero_leakage.py -v

# 2. 驗證快慢雙軌特徵識別、偽陽性過濾與本機 Gemma 個性化生成
pytest testing/m4_12/test_dual_track_eval.py -v

# 3. 驗證 M1.2 微斷點心流守門、驚喜彈窗推播與開機單上限 (Single Cap) 補發
pytest testing/m4_12/test_flow_gated_broadcast.py -v

# 4. 驗證本機 Gemma 離線或逾時之待命佇列暫存與出隊重試
pytest testing/m4_12/test_offline_queue.py -v

# 5. 驗證 M6.5 ACID 交易原子寫入與 XP 核發冪等性
pytest testing/m4_12/test_acid_settlement.py -v

# 全量回歸測試
pytest testing/m4_12/ -v
```

---

## 3. 手動與端到端互動調試 (Manual E2E Scenarios)

### Scenario A: 驗證未解鎖成就之零資料洩漏 (Zero-Leaked State)

1. **啟動後端服務**：
   ```bash
   uvicorn services.main:app --port 8000 --reload
   ```

2. **發送查詢請求**：
   ```bash
   curl -s http://localhost:8000/api/achievements?user_id=test_user | jq .
   ```

3. **預期結果**：
   - 回傳 JSON 僅包含常規已公開成就及該使用者**已解鎖**的成就。
   - `items` 陣列中絕對無任何 `is_hidden: true` 且尚未解鎖之物件；無問號標籤、無「還有 X 個未解鎖」之計數。

---

### Scenario B: 觸發快軌主動探究與微斷點驚喜彈窗 (Fast-Path & Flow-Gated Surprise)

1. **連線至 WebSocket 監聽**：
   ```bash
   wscat -c ws://localhost:8000/api/m4_12/ws?user_id=test_user
   ```

2. **模擬使用者送出包含深層技術追問之對話訊息**：
   ```bash
   # 模擬對話發送，內含高階概念主動探究
   curl -X POST http://localhost:8000/api/m4_12/test/simulate_message \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test_user",
       "role_id": "role_csie",
       "message": "我想知道這段程式碼在編譯成 LLVM IR 時，LLVM 是如何透過 SSA 形式進行 Dead Code Elimination 的？"
     }'
   ```

3. **模擬使用者當前處於連續打字中（Deep Flow）**：
   - 系統內部觸發特徵命中，但監測到 M4.8 / M1.2 心流保護狀態，解鎖通知暫存於佇列中，WebSocket 暫無事件送出。

4. **模擬使用者送出訊息後停頓（觸發 M1.2 微斷點）**：
   ```bash
   curl -X POST http://localhost:8000/api/m1_2/simulate_breakpoint \
     -H "Content-Type: application/json" \
     -d '{"breakpoint_type": "message_turn_pause", "pause_seconds": 3.5}'
   ```

5. **預期結果**：
   - WebSocket 立即收到事件：
     ```json
     {
       "event_type": "HIDDEN_ACHIEVEMENT_UNLOCKED",
       "achievement_id": "ha_curious_cartographer_01",
       "archetype": "curiosity",
       "name": "本質探求者",
       "rarity": "rare",
       "exp_reward": 100,
       "flavor_text": "「你所觸碰的不是表象，而是深邃的知識核心。」"
     }
     ```
   - 前端接收後跳出 `SurpriseModal`，關閉後發送 `ACK_SURPRISE_MODAL`。

---

### Scenario C: 模擬 Gemma 離線佇列待命與背景重試 (Offline Queue Fallback)

1. **將本地模型開關設為離線**：
   ```bash
   export M2_2_GEMMA_AVAILABLE=0
   ```

2. **提交每日反思（包含元認知轉折反思）**：
   ```bash
   curl -X POST http://localhost:8000/api/m6_4/reflections \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test_user",
       "user_feeling": "原本因為功能重構失敗感到非常挫折與防衛，但我冷靜對照薩提爾冰山後，意識到自己過度把自尊綁定在一次提交上，我學會了接納不完美。",
       "user_action_plan": "明天改以最小切片 TDD 逐步驗證。"
     }'
   ```

3. **檢查離線佇列狀態**：
   ```bash
   curl -s http://localhost:8000/api/m4_12/queue/status | jq .
   ```
   - 預期回傳：`{"pending_count": 1, "processing_count": 0, "failed_count": 0}`，反思提交順暢完成未卡死。

4. **喚醒本機模型並觸發排程補算**：
   ```bash
   export M2_2_GEMMA_AVAILABLE=1
   curl -X POST http://localhost:8000/api/m4_12/queue/drain
   ```
   - 佇列順利清空，解鎖 `THE_REFRAME_ALCHEMIST`（心靈煉金術士）並入庫。
