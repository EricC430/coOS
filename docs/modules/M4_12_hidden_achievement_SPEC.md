# M4.12 — 隱藏成就驗證引擎 (Hidden Achievement Verification Engine)

**標籤**:`[進階-Feature 003]`  
**版本**:`1.0` / `released`  
**最後更新**:2026-10-20  

---

## 1. Purpose (模組目的)

M4.12 隱藏成就驗證引擎以「零負擔感、無預警驚喜、全域激勵」為設計核心，透過背景無感監聽對話與反思，捕捉使用者自主進行深度探究、元認知自省、注意力恢復實踐與跨領域融通之火花。

嚴格遵守 **coOS Constitution 1.1.0** 與 **CLAUDE.md** 核心架構約束：
1. **三層隱私架構 (Three-Tier Privacy)**：所有特徵捕捉與語意分析均在本機 SQLite 與本機 Gemma (M2.2) 完成，L1 對話明文 0% 上傳雲端。
2. **零洩漏狀態 (M3.11.3 Zero-Leaked State)**：未解鎖隱藏成就於 SQL 查詢層與 API 序列化層強制隔離，前端成就牆 0 佔位 DOM 節點，徹底消除 FOMO 與逆向破解動機。
3. **心流微斷點門禁 (RISK-04 Flow-Gated Surprise)**：高認知負荷或連貫打字時通知暫存於記憶體佇列，僅於 M1.2 自然任務斷點（停頓思考、對話交接）進行 WebSocket 廣播。
4. **零質押與純純粹獎勵 (Zero-Staking)**：隱藏成就僅給予純 XP 與個人專屬金句獎勵，嚴禁質押扣款或失敗懲罰。
5. **ACID 交易原子性與終身防重解鎖**：同一成就單一使用者終身限解鎖 1 次，具備 60 秒滑動視窗防刷保護與 M0.4 結構化稽核日誌。

---

## 2. References (引用研究與憲法依據)

| 編號 | 章節 / 規則 | 應用點 |
| ---- | ----------- | ------ |
| coOS Constitution 1.1.0 | Principle I: 三層隱私架構 | L1 本地嚴格隔離，Epistemic 語意解析完全本機化 |
| coOS Constitution 1.1.0 | Principle II: 心理不變量 | M3.11.3 零洩漏狀態，RISK-04 心流微斷點推播，Zero-Staking |
| R01 | §動態邊界 (Dynamic Boundaries) | 學習者超越常規指針時的自主概念跳躍探究捕捉 |
| R08 | §二 Defer-to-Breakpoint | 心流不打擾原則，避免中斷使用者的深層專注 |

---

## 3. Submodules & Responsibilities (子模組職責)

| 子模組 | 職責說明 | 核心實作檔案 |
| ------ | -------- | ------------ |
| **M4.12.1** | **主動探索特徵捕捉網**: 快慢雙軌混合架構。快軌正則 <100ms 預先過濾，慢軌本機 Gemma 解析認知跳躍深度與主動提問權重，具備離線與逾時 (>3s) 暫存佇列與補算守護器。 | `feature_trap.py`<br>`evidence_queue.py` |
| **M4.12.2** | **心流微斷點推播與即時廣播**: 整合 M1.2 斷點偵測與 M4.8 負荷信號，深層心流時暫存通知；微斷點透過 WebSocket 推送 `HIDDEN_ACHIEVEMENT_UNLOCKED`；開機/重連執行 Single Cap (至多 1 筆彈窗)。 | `surprise_dispatcher.py`<br>`router.py` |
| **M4.12.3** | **零洩漏狀態隔離**: 於 SQL 查詢層強制執行 `WHERE is_hidden = 0 OR (is_hidden = 1 AND id IN (SELECT ...))`，成就牆分母完全排除未解鎖之隱藏成就，DOM 0 佔位。 | `router.py`<br>`AchievementGrid.tsx` |
| **M4.12.4** | **四大核心成長原型與金句生成**: 實作好奇探險家、心靈煉金術士、微光漫遊者、通識織網者規則評估器與本機 Gemma 個性化專屬金句合成。 | `archetypes.py`<br>`feature_trap.py` |
| **M4.12.5** | **ACID 結算與防刷遙測**: 整合 M6.5 `XPGatekeeper` 原子寫入 `user_achievements` 與 XP 核發，60 秒滑動視窗防刷，M0.4 [R01] 結構化日誌記錄。 | `service.py`<br>`rate_limiter.py`<br>`telemetry.py` |

---

## 4. Four Core Archetypes (四大核心成長原型)

1. **THE_CURIOUS_CARTOGRAPHER (本質探求者)**
   - **原型分類**: `curiosity` | **稀有度**: `rare` | **XP 獎勵**: 100
   - **檢驗條件**: 主動追問底層原理達五層以上（正則匹配底層、IR、SSA、編譯器、AST、虛擬機器等核心原理與為什麼/機制）。
   - **金句範本**: 「你所觸碰的不是表象，而是深邃的知識核心。」

2. **THE_REFRAME_ALCHEMIST (心靈煉金術士)**
   - **原型分類**: `metacognition` | **稀有度**: `epic` | **XP 獎勵**: 150
   - **檢驗條件**: 於每日反思中體察自我心理阻抗與脆弱，完成薩提爾冰山心態重構與自我接納。
   - **金句範本**: 「接納不完美的那一刻，真正的轉化已經開始。」

3. **THE_SERENDIPITY_SEEKER (微光漫遊者)**
   - **原型分類**: `restoration` | **稀有度**: `rare` | **XP 獎勵**: 80
   - **檢驗條件**: 高認知負荷時果斷走向實體生活實踐注意力恢復 (ART)，包含散步、烹飪、大自然五感覺察。
   - **金句範本**: 「微風與綠意撫平了焦慮，世界在此刻向你敞開。」

4. **THE_POLYGLOT_SYNTHESIZER (通識織網者)**
   - **原型分類**: `cross_synthesis` | **稀有度**: `legendary` | **XP 獎勵**: 250
   - **檢驗條件**: 跨越不同角色與領域（如哲學與演算法、心理學與系統架構），建立概念類比與深層知識融通。
   - **金句範本**: 「當邊界消融，跨界的火花照亮了未知的群島。」

---

## 5. API & WebSocket Specifications

### Endpoints

- **`GET /api/achievements`**: 取得已解鎖成就總覽 (嚴格零洩漏)。
  - Query: `user_id` (str), `role_id` (optional str)
  - SQL Guard: 強制過濾未達成之隱藏成就
  - Response: `AchievementWallResponse` (包含 `total_unlocked_count`, `total_visible_count`, `items`)
- **`POST /api/achievements/ack`**: 確認已讀驚喜彈窗。
  - Body: `{"user_id": str, "achievement_ids": list[str]}`
  - Effect: 將 DB 記錄之 `is_acknowledged` 置為 1。
- **`GET /api/m4_12/queue/status`**: 查詢離線特徵佐證暫存佇列健康狀態。
  - Response: `{"pending_count": int, "processing_count": int, "failed_count": int}`
- **`WebSocket /api/m4_12/ws`**: 驚喜事件即時雙向通道。
  - Server -> Client: `{"event_type": "HIDDEN_ACHIEVEMENT_UNLOCKED", ...}`
  - Client -> Server: `{"action": "ACK_SURPRISE_MODAL", "achievement_id": str}`

---

## 6. Verification & Test Suite

所有核心能力均經過完整的自動化單元與整合測試驗證：

| 測試檔案 | 驗證範疇 | 狀態 |
| -------- | -------- | ---- |
| `testing/m4_12/test_dual_track_eval.py` | 快軌正則 (<100ms)、慢軌語意跳躍深度、Gemma 逾時離線佇列暫存 | ✅ PASSED (5/5) |
| `testing/m4_12/test_zero_leakage.py` | SQL 層強制過濾、API 回傳 0% 洩漏未解鎖項目、分母排除 (含公開成就防重複計數) | ✅ PASSED (4/4) |
| `testing/m4_12/test_flow_gated_broadcast.py` | M1.2 心流感知門禁、暫存佇列釋放、ACK 更新、開機 Single Cap 補發 | ✅ PASSED (3/3) |
| `testing/m4_12/test_archetype_rules.py` | 四大核心原型自定義評估器、本機 Gemma 個性化金句生成 | ✅ PASSED (5/5) |
| `testing/m4_12/test_acid_settlement.py` | 60 秒滑動視窗防刷、併發 ACID 冪等解鎖 (含 IntegrityError 自動 rollback)、M0.4 遙測無 L1 明文 | ✅ PASSED (4/4) |

**全量測試執行指令**:
```bash
py -3.10 -m pytest testing/m4_12/
```
