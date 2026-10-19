# Phase 0: Technical Research & Architecture Decisions

**Feature**: M4.11 動態邊界任務池與 ZPD 盲盒管線 (Dynamic ZPD Gacha Pipeline)  
**Date**: 2026-10-19  
**Status**: Completed  

---

## 1. Multimodal BKT (Bayesian Knowledge Tracing) Mathematical Formulation

### Decision
採用**多模態貝氏知識追蹤（Multimodal BKT）**模型維護各角色的技能掌握度機率 $P(L_t)$，並將其動態映射至近側發展區（ZPD）難度區間 $[zpd_{lower}, zpd_{upper}]$。

#### 數學模型公式化：
1. **基礎參數**：
   * 先驗機率 $P(L_0) = 0.30$（冷啟動預設值）
   * 學習轉移率 $P(T) = 0.15$（完成一次挑戰後由未掌握轉為掌握的機率）
   * 猜測率 $P(G) = 0.10$（未掌握但意外成功的機率）
   * 失誤率 $P(S) = 0.10$（已掌握但遭遇阻力失敗的機率）
2. **貝氏後驗機率更新**（以挑戰成功/失敗事件 $O_t \in \{1, 0\}$ 為依據）：
   * 若挑戰成功 ($O_t = 1$)：
     $$P(L_t \mid O_t = 1) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$
   * 若挑戰過期/放棄 ($O_t = 0$)：
     $$P(L_t \mid O_t = 0) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$
   * 狀態前向預測：
     $$P(L_{t+1}) = P(L_t \mid O_t) + (1 - P(L_t \mid O_t)) \cdot P(T)$$
3. **多模態權重調節因子（M4.8 融合）**：
   * 引入完成耗時比 $\gamma = \frac{\text{actual\_minutes}}{\text{estimated\_minutes}}$ 與反思情緒權重 $\omega$。若 $\gamma > 1.5$ 且反思中包含高掙扎詞彙，則適度調高失誤率 $P(S)$，避免過度高估掌握度。
4. **ZPD 邊界映射**：
   * $zpd_{lower} = \max(0.1, P(L_t) - 0.20)$
   * $zpd_{upper} = \min(0.95, P(L_t) + 0.25)$

### Rationale
* 符合文獻 `[R01: ZPD 量化與 RLHF 自動化難度調節 §動態追蹤]`，以機率化方式捕捉使用者的能力演進，杜絕固定靜態題目設定。
* 計算複雜度為 $O(1)$，可在本地端毫秒級完成更新，完全不耗費額外 GPU 資源。

### Alternatives Considered
* **傳統 ELO 積分制**：常用於對戰棋類，但對單人技能掌握度缺少「知識狀態轉移（Learning Transition）」的概念，容易因偶然失敗而大幅震盪，增加挫敗感。
* **深度知識追蹤（DKT, RNN/LSTM）**：需要大量先驗大數據預訓練模型，違反桌面本地輕量與冷啟動原則。

---

## 2. ZONE 框架 REJECT + GRAD 抽樣與機緣生活任務融合

### Decision
實作 **ZONE 框架雙階篩選演算法**，結合「專業挑戰（Skill Stretch）」與「框架外生活恢復任務（Restorative & Serendipity Tasks）」，並導入認知負荷自適應權重提升機制。

#### 演算法流程：
1. **任務類別判定（雙軌動態切換）**：
   * 讀取 M4.8 當前狀態。若偵測到 `anxiety`、`avoidance` 或連續專注超過 120 分鐘（`directed_attention_fatigue`）：
     * 恢復型生活任務（`restorative_serendipity`）權重提升至 **70%**，專業技能任務降為 **30%**。
   * 一般/心流狀態：
     * 專業技能任務佔 **85%**，生活機緣驚喜卡佔 **15%**。
2. **階梯梯度抽樣（GRAD）**：
   * 若抽中專業任務：
     * `REJECT`：候選難度 $d \notin [zpd_{lower}, zpd_{upper}]$ 則剔除。
     * `GRAD`：將候選任務按難度分層（`comfort`: 20%, `just-manageable`: 60%, `stretch`: 20%）。高認知負荷時強制將 `stretch` 權重歸零（安全退縮）。
   * 若抽中生活恢復任務：
     * 難度固定為 `restorative`，時長強制 $\le 20$ 分鐘，標記 `is_real_world: true`。

### Rationale
* 依據 `[R01: ZONE 框架 §理論基礎]` 與注意力恢復理論（ART），保證任務既能在心流區（Flow Zone）拓展邊界，又能在腦力耗竭時提供軟性著迷（Soft Fascination）的實體生活休息窗口。

### Alternatives Considered
* **均等隨機抽取**：忽略使用者當前認知疲勞，在高壓時依然可能抽出高難度演算法題，觸發 `[RISK-09]` 與 `[R01: Dropout 危機]`。
* **前端手動切換頁籤（Tab）**：破壞盲盒「不期而遇的驚喜感」，增加操作微阻力。

---

## 3. 全 LLM 動態生成架構與雙階降級備援機制

### Decision
採用 **全 LLM 動態生成** 作為主要管線，並以 **領域預載種子庫 + 參數化槽位填充（Curated Seeds + Slot Filling）** 作為極速離線/超時降級備援。

#### 執行策略：
1. **主管線（On-device / Cloud LLM）**：
   * 收集輸入信號：
     * `role_id` 與技能領域
     * 近 24 小時 `chat_transcripts` 萃取出的 `interest_topic` 與 `friction_point`
     * BKT 難度區間 $[zpd_{lower}, zpd_{upper}]$
     * 當前認知負荷等級
   * 構建結構化 Prompt（強制以 JSON 輸出符合 `ZPDChallenge` 規格）。
   * 超時閾值設定為 **5.0 秒**。
2. **雙階降級備援（Dual-Tier Fallback）**：
   * 優先順序：本機 Gemma (M2.2) $\to$ 去識別化雲端 LLM $\to$ 本地種子槽位填充。
   * 若 LLM 推論失敗、斷網或超過 5 秒，降級引擎立即自本地 SQLite / JSON 的 `seed_challenges` 挑選符合領域之種子，將對話關鍵字填入範本槽位中，於 **<300ms** 內完成組裝並返回。

### Rationale
* 滿足憲法 Principle I（L1 本地隱私）與離線優先約束（Offline-First）。
* 保證前端抽卡按鈕響應體驗平滑，永不卡死或報錯轉圈。

### Alternatives Considered
* **純靜態題庫**：內容呆板，無法呼應使用者當下對話中的真實卡關痛點。
* **純 LLM 無降級**：一旦本機無 GPU 或外出斷網，抽卡功能即刻癱瘓，違反桌面端本機可用原則。

---

## 4. 單一活躍挑戰槽位與軟性過期生命週期

### Decision
採用**單一進行中槽位（Single Active Slot）**與**次日凌晨軟性自然過期（Soft Expiration at Day-End / 24h）**。

#### 狀態流轉圖：
```
[Generated] ──(抽中展示)──> [Generated Card]
                               │
            ┌──────────────────┴──────────────────┐
            ▼ (點擊接受)                            ▼ (點擊放棄/保留原挑戰)
        [Accepted]                              [Discarded]
            │
    ┌───────┴───────────────────────┐
    ▼ (完成並填寫反思)                ▼ (超過 24h / 次日 04:00 AM)
[Completed] (M6.5 ACID XP)      [Expired] (0 XP 懲罰)
```

#### 規則定義：
1. **單一槽位**：每個角色同一時間僅能有 1 個 `status = 'accepted'` 的任務。若抽到新任務，使用者必須選擇「替換目前挑戰」或「保留原挑戰」。
2. **零懲罰過期**：任務過期時自動標記為 `expired`，BKT 以 $O_t = 0$ 輕微衰減後驗機率，但**絕對不扣除使用者任何現有 XP**（落實 RISK-07 與憲法原則 II）。

### Rationale
* 防止「任務囤積症」帶來的待辦焦慮與無力感（Todo List Guilt）。
* 軟性跨日結轉配合人類作息節奏，避免分秒倒數計時器造成的緊迫時間壓迫感。

### Alternatives Considered
* **多任務列表（Quest Log）**：容易囤積數十個未完成挑戰，使用者最後索性不再打開該模組。
* **分秒倒數硬性計時器**：計時器歸零直接判定失敗並扣分，嚴重違反心理安全與變動增強原則。
