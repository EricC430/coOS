# Feature Specification: M4.12 隱藏成就驗證引擎 (Hidden Achievement Verification Engine)

**Feature Branch**: `003-m4-12-hidden-achievement`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "/speckit-specify 進行M4.12的重新設計、分析與描述"

## Clarifications

### Session 2026-10-20
- Q: M4.12 背景特徵捕捉網之觸發架構與評估頻率為何？ → A: 快慢雙軌混合架構（Hybrid Dual-Track）：每則對話訊息發送後由本地輕量嵌入/正則進行快速候選預篩（Fast Path，<100ms）；於會話結束或 M6.4 每日反思提交時，由本機 Gemma (M2.2) 進行深度語意與元認知評估（Slow Path）。兼具即時感與複雜語意理解，且運算開銷最適化。
- Q: 當使用者處於連續高頻工作、深度專注（Flow）或高認知負荷（M4.8）時，隱藏成就解鎖廣播應如何呈現？ → A: 微斷點排隊延遲投遞（Flow-Gated Micro-Breakpoint）：解鎖後先行完成 M6.5 資料庫 ACID 交易入庫，解鎖廣播暫存於佇列，等待 M1.2 偵測到自然微斷點（如送出下一句對話、完成當前挑戰切片、切換視窗暫歇）才彈出 `SurpriseModal`，杜絕打斷深層心流（RISK-04、CLAUDE.md 第二條）。
- Q: 隱藏成就庫的定義規格與擴充策略為何？ → A: 核心原型 + 領域動態參數 + 本機 AI 個性化生成（Hybrid Archetype Engine with Dynamic AI Synthesis）：以四大核心成長原型（探究、元認知、生活恢復、跨領域）為骨幹，各角色領域依技能樹動態載入關鍵概念詞網；同時允許本機 Gemma (M2.2) 在偵測到深度個人化突破時，在原型槽位下動態生成專屬成就標題、文案與啟發金句，兼具系統平衡性、測試確定性與個人化驚喜。
- Q: 當本機 Gemma（M2.2）處於離線、未載入或推論逾時狀態時，M4.12 慢軌（Slow Path）應採用何種降級備援策略？ → A: 延遲佇列待命重試（Queued Evaluation）：將待評估之特徵佐證寫入本機 SQLite 暫存佇列（`epistemic_evidence_queue`），維持離線不阻塞主對話；待本機模型就緒或系統資源充足時再行背景補算、解鎖與推播。
- Q: 隱藏成就的歸屬與作用域應綁定於特定單一角色，還是歸屬於使用者全域帳號？ → A: 全域帳號擁有，標註來源角色（Global User Scope with Origin Role Tag）：隱藏成就歸屬於全域使用者帳號（`user_id`），成就牆跨角色共用；在 `UserAchievementRecord` 中記錄 `origin_role_id`，兼顧全域成長脈絡與跨領域思維融合（`THE_POLYGLOT_SYNTHESIZER`）。
- Q: 當使用者在離線、客戶端關閉期間達成隱藏成就，或因連線中斷錯失即時 WebSocket 廣播時，下次開啟客戶端時應如何補發該解鎖驚喜？ → A: 開機至多 1 個精選彈窗，其餘靜默標記 NEW（Single Cap with High-Watermark Priority）：啟動或重新連線時若有積壓之未確認成就，最多僅展示 1 個稀有度最高之 `SurpriseModal`，其餘成就安靜入庫並於成就總覽點亮附帶「NEW」標籤，避免連續彈窗干擾啟動體驗。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 主動探索與高階概念跳躍之背景無感驗證 (Priority: P1)

作為一名在特定領域深耕或學習的使用者，當我在與 AI 助理對話、撰寫日報或解決問題時，主動跳脫既定提示、深入探索底層本質或跨越目前能力前沿（ZPD）時，我希望系統能在背景敏銳捕捉到這種「主動求知」的火花並自動驗證達成隱藏成就，而不需要我自己手動申請或被刻板的檢查清單束縛。

**Why this priority**:
這是 M4.12 核心存在的心理學價值。傳統遊戲化將目標明確列出，容易引發過度辯護效應（Overjustification Effect）與功利性刷點數行為；M4.12 透過「主動探索特徵捕捉網（M4.12.1）」，保護內在動機，獎勵非功利性的深探與好奇心。

**Independent Test**:
- 於測試資料庫中注入一段包含使用者自主深究高階概念（例如在無任務要求下，自主提問並解析系統底層排程演算法）的對話事件，驗證 M4.12.1 背景分析器在指定時限內完成特徵辨識並判定達成 `THE_CURIOUS_CARTOGRAPHER` 隱藏成就。
- 驗證全程資料均在本地端完成特徵分析，無任何未脫敏之 L1 明文對話上傳雲端（遵循 Constitution Principle I）。

**Acceptance Scenarios**:
1. **Given** 使用者在對話中並非由 AI 主動引導，而是自主發起連續多層的本質追問或嘗試進階概念實作，**When** M4.12.1 背景特徵網掃描對話語意與提問模式，**Then** 系統判定命中主動探索特徵，觸發解鎖流程。
2. **Given** 使用者僅是隨機提及特定高難度關鍵字（例如複製貼上術語但無實質探究脈絡），**When** M4.12.1 進行語意與認知深度驗證，**Then** 系統正確過濾偽陽性，不觸發解鎖，防止刷成就行為。

---

### User Story 2 - 絕對無痕的隱藏狀態與零資料洩漏隔離 (Priority: P2)

作為一名追求專注與內在平靜的使用者，在尚未觸發任何隱藏成就之前，我希望在系統任何畫面（包含成就總覽、技能樹、統計進度條、DOM 結構與網路 API 回傳內容）中，都絕對看不到未解鎖隱藏成就的任何蛛絲馬跡（無問號格位、無「剩餘 X 個隱藏成就」計數、無灰色佔位），杜絕錯失恐懼症（FOMO）。

**Why this priority**:
落實 `CLAUDE.md` 第二條與 M3.11.3「絕對無 UI 狀態」鐵律。只要介面有一絲暗示，使用者就會轉移注意力去猜測條件或逆向破解，徹底摧毀「無預警驚喜」與無壓力成長環境。

**Independent Test**:
- 呼叫成就查詢 API（如 `GET /api/achievements`）及檢視桌面端 DOM 結構，檢驗當前使用者未解鎖之所有隱藏成就。
- 驗證後端 API 回傳清單完全過濾未解鎖隱藏項目（洩漏率 0%），且成就總數與百分比統計不含未解鎖之隱藏成就基數。

**Acceptance Scenarios**:
1. **Given** 系統成就資料庫中預置有 10 個隱藏成就，使用者尚未解鎖任何一項，**When** 使用者開啟成就牆或發起資料查詢，**Then** API 回傳與前端渲染中完全不包含這 10 個隱藏成就的 ID、標題、計數或灰色問號格位。
2. **Given** 使用者透過瀏覽器 DevTools 或網路代理檢查 API 回傳 JSON，**When** 搜尋隱藏成就欄位，**Then** 僅能看到已公開成就，不存在任何未解鎖隱藏成就的元資料外洩。

---

### User Story 3 - 心流感知的無預警即時驚喜廣播與排隊 (Priority: P3)

作為一名剛完成一項意外突破的使用者，當隱藏成就達成時，我希望在合適的心理時機收到無預警的驚喜彈窗與激勵反饋；但若我正處於高度專注（Deep Flow）或高度焦慮狀態時，系統不應粗暴打斷我的思考節奏，而是靈巧地在微斷點（Breakpoint）呈現。

**Why this priority**:
連結 R01 變動比例增強理論與 M1.2 斷點偵測、M3.11.4 驚喜彈窗。驚喜的威力在於意外感，但意外感不能以犧牲使用者當前心流或引發認知干擾為代價。

**Independent Test**:
- 模擬使用者處於高度認知專注期間解鎖隱藏成就，驗證 M4.12.2 將解鎖廣播暫存，等待 M1.2 斷點信號發布後立即送出 WebSocket 事件。
- 前端接收到 WebSocket 事件後，成功以 `SurpriseModal` 展示徽章特效、讚賞文案與 XP 獎勵。

**Acceptance Scenarios**:
1. **Given** 使用者在對話或反思完成時達成隱藏成就，且當前無高負載工作，**When** M4.12.2 觸發解鎖，**Then** 500ms 內透過 WebSocket 推送 `HIDDEN_ACHIEVEMENT_UNLOCKED` 事件，前端立即跳出驚喜彈窗並播放音效/微動畫。
2. **Given** 系統偵測到使用者正處於連續鍵盤高頻輸入或深層工作期間，**When** 隱藏成就條件達成，**Then** 系統自適應將彈窗通知延遲至下一個動作微斷點（如訊息送出後或單元切換時），保障心流不中斷。
3. **Given** 使用者在短時間內連續觸發多個隱藏成就，**When** 彈窗推送至前端，**Then** 系統遵循 FIFO 佇列機制依序展示，不互相覆蓋或產生疊層混亂。

---

### User Story 4 - 多元成長原型驗證：元認知、生活恢復與跨領域共融 (Priority: P4)

作為一名多維度成長的使用者，我希望隱藏成就的探索範疇不僅限於硬核專業技術，更能涵蓋「承認認知偏誤/心態轉化（薩提爾冰山實踐）」、「在疲憊時果斷走向大自然的實體生活恢復」以及「將兩種截然不同領域知識進行跨界融合」，肯定我身為完整人的各面向突破。

**Why this priority**:
契合 coOS 融合薩提爾心理模型、注意力恢復理論（ART）與全人發展願景。隱藏成就應引導使用者看見自身盲點、尊重身心節奏，而非僅鼓勵單一維度的技術內捲。

**Independent Test**:
- 分別注入包含「自省並放下防衛心態（冰山重構）」、「連續專注 2 小時後主動外出散步 20 分鐘並拍照反思」、「在角色 A 的問題中巧妙引用角色 B 概念」之情境數據。
- 驗證 M4.12 分別辨識並核發對應原型成就（如 `THE_REFRAME_ALCHEMIST`, `THE_SERENDIPITY_SEEKER`, `THE_POLYGLOT_SYNTHESIZER`）。

**Acceptance Scenarios**:
1. **Given** 使用者在 M6.4 每日反思中承認了先前的心理阻抗並重構行動方案，**When** M4.12.1 評估反思語意深度與自我接納度，**Then** 成功解鎖元認知突破型隱藏成就。
2. **Given** 使用者在 M4.8 疲勞信號下主動選擇完成生活恢復型挑戰，**When** 驗證通過，**Then** 觸發生活滋養型隱藏成就，讚許其知所進退的自省勇氣。

---

### User Story 5 - M6.5 ACID 交易寫入、XP 激勵與防刷機制 (Priority: P5)

作為一名系統架構守護者，我希望所有隱藏成就的解鎖與經驗值核發均透過 M6.5 ACID 守門員進行嚴格交易鎖定，具備完全的冪等性（Idempotency），絕不發生重複發放、掉單或並發競態異常。

**Why this priority**:
符合專案憲法 Principle II（XP Gatekeeper）與 Principle VII（可觀測性）。遊戲化經濟系統的誠信與穩定是系統長期運行的基石。

**Independent Test**:
- 併發發送 5 次針對同一使用者相同隱藏成就的解鎖請求，驗證 M6.5 僅成功寫入 1 筆 `user_collections` 紀錄，XP 僅增加一次，其餘請求平滑返回已解鎖狀態。
- 驗證所有解鎖動作均向 `raw_tracking_logs` 發布具備完整結構（模組標籤、成就 ID、時間戳、耗時、驗證信心度）的事件紀錄。

**Acceptance Scenarios**:
1. **Given** 一項隱藏成就被判定達成，**When** 呼叫解鎖結算管道，**Then** 系統於同一資料庫交易內寫入 `user_collections` 並更新用戶 XP 帳本，寫入失敗時全量 rollback。
2. **Given** 系統崩潰或網路重試，**When** 再次執行已解鎖成就的驗證邏輯，**Then** 系統直接識別已解鎖狀態並靜默略過，不重複推送廣播與 XP。

---

### Edge Cases

- **極端對話長度或大量訊息灌水**：
  若使用者快速發送大量訊息或貼入長篇複製文字試圖觸發關鍵字，M4.12.1 應設置滑動視窗防護與文字熵值檢驗，拒絕單純重複性文字，且單一 session 內背景特徵掃描頻率限制在合理閾值（如每分鐘不超過 10 次檢驗）。
- **離線或弱網環境下的成就達成**：
  當使用者在離線狀態下滿足本機隱藏成就條件時，本地 SQLite 立即完成解鎖記錄（`is_acknowledged = false`）與 XP 本地結算；待重新連線或重啟客戶端時，遵循 FR-015 之上限規則，最多補發 1 個最高稀有度之驚喜彈窗，其餘標註「NEW」徽章入庫，避免開機連續彈窗刷屏 [Clarification Session 2026-10-20 Q6]。
- **本機 Gemma 離線或推論逾時 (Slow Path Fallback)**：
  當本機 Gemma（M2.2）未載入、處於離線狀態或推論超時（>3 秒），慢軌不會丟失評估機會，而是將特徵佐證安全寫入本地 SQLite 之 `epistemic_evidence_queue` 表中。系統設有背景輪詢守護器，待模型喚醒或資源空閒時依序出隊補算解鎖，補發之成就仍能獲得完整經驗值與回顧紀錄 [Clarification Session 2026-10-20 Q4]。
- **高焦慮與心理危機狀態下的干擾防護 (RISK-09)**：
  當 M4.8 輸出標記當前情緒為高度焦慮或崩潰臨界時，系統暫停所有慶祝型強烈聲光彈窗推送，轉為靜默入庫，待情緒恢復平穩或下一次主動開啟成就面板時再行溫和提示。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系統 MUST 實作 M4.12.1 主動探索特徵捕捉網，於背景監聽使用者對話歷史、每日反思內容與任務實作記錄，萃取主動求知與深鑽特徵。
- **FR-002**: 系統 MUST 支援宣告式隱藏成就定義架構（`HiddenAchievementDefinition`），支援設定觸發原型（Archetype）、語意條件、前置狀態依賴與獎勵權重。
- **FR-003**: 系統 MUST 包含至少四種核心成長原型隱藏成就：
  1. `THE_CURIOUS_CARTOGRAPHER`（自主高階概念跨越與深鑽）
  2. `THE_REFRAME_ALCHEMIST`（薩提爾冰山元認知反思與心理盲點突破）
  3. `THE_SERENDIPITY_SEEKER`（脫離螢幕的實體生活探索與注意力恢復實踐）
  4. `THE_POLYGLOT_SYNTHESIZER`（跨角色、跨領域之結構性知識整合）
- **FR-004**: M4.12.1 特徵檢驗評估管線 MUST 實作**快慢雙軌混合觸發架構（Hybrid Dual-Track Architecture）**：
  - **快軌（Fast Path）**：每則使用者訊息傳送後，於背景藉由本地輕量正則特徵網與本地向量嵌入快速過濾候選特徵（<100ms），針對明確關鍵跳躍觸發初步命中。
  - **慢軌（Slow Path）**：於對話會話結束（Session Idle > 5 分鐘）或 M6.4 每日反思提交時，調用本機 Gemma（M2.2）進行深層語意、心理盲點突破與元認知跳躍評估，確保深刻思考與心態轉折被完整識別 [Clarification Session 2026-10-20 Q1]。
  - **離線與推論逾時佇列（Offline & Timeout Queue）**：若本機 Gemma（M2.2）處於離線、未載入或推論逾時（>3 秒），系統將待評估佐證寫入本機 SQLite 之 `epistemic_evidence_queue`，待模型就緒或系統閒置時非同步出隊重試評估，絕不阻斷對話或反思主流程 [Clarification Session 2026-10-20 Q4]。
- **FR-005**: 系統 MUST 保證隱藏成就驗證過程嚴格遵守 Constitution Principle I L1 隱私規範：所有對話與反思文本之語意分析 100% 於本地端（SQLite / 本機 Gemma M2.2）執行，未去識別化之明文絕對不上傳雲端。
- **FR-006**: 系統 MUST 嚴格實現 M3.11.3「絕對無 UI 狀態」隔離：
  - 後端 `GET /api/achievements` 等所有公開查詢端點 MUST 在 SQL/查詢層強制過濾未解鎖隱藏成就（`WHERE is_hidden = false OR (is_hidden = true AND unlocked_at IS NOT NULL)`）。
  - 前端元件、全域 Store、成就總數進度條等，0% 洩漏未解鎖隱藏成就之 ID、名稱、問號佔位符或存在計數。
- **FR-007**: 系統 MUST 實作 M4.12.2 無預警即時解鎖廣播器，當驗證通過時，透過 WebSocket/SSE 向前端推播 `HIDDEN_ACHIEVEMENT_UNLOCKED` 事件。
- **FR-008**: 系統解鎖廣播時機 MUST 實作**心流感知微斷點排隊機制（Flow-Gated Micro-Breakpoint Delivery）**：
  - 當 M4.12 判定成就達成時，系統立即於背景完成 M6.5 ACID 交易寫入；
  - 若 M4.8 或 M1.2 偵測使用者正處於連續鍵盤輸入、深度心流（Flow）或高認知負荷狀態，解鎖通知暫存於本機記憶體佇列；
  - 待 M1.2 發布自然微斷點事件（如使用者完成訊息送出、任務切片完成、或短暫停頓切換視窗）時，立即透過 WebSocket 廣播觸發 M3.11.4 `SurpriseModal`，絕不於深思或編程敲鍵中途粗暴打斷心流 [Clarification Session 2026-10-20 Q2, RISK-04]。
- **FR-009**: 隱藏成就之定義與延伸庫擴充機制 MUST 實作**核心原型結合本機 AI 個性化動態生成（Hybrid Archetype & Dynamic AI Synthesis）**：
  - **靜態骨幹**：以系統預定義之四大核心成長原型（探究、元認知、生活恢復、跨領域）作為不可變的架構基座與 XP 經濟常數。
  - **領域參數化**：各領域角色（`RoleContext`）依技能樹動態注入專屬技術/知識概念詞網與判定規則。
  - **AI 個性化金句與稱號**：當捕捉到獨特的個人轉化或突破時，本機 Gemma（M2.2）在所屬原型規範內，動態為該次解鎖生成專屬之成就副稱號、探索脈絡描述與啟發性心理金句（`flavor_text`），並寫入 `UserAchievementRecord.context_summary`，賦予唯一的個人化紀念價值 [Clarification Session 2026-10-20 Q3]。
- **FR-010**: 解鎖成就結算 MUST 經由 M6.5 ACID Gatekeeper 執行，將資料原子寫入 `user_collections` 表與 XP 帳本，並保證操作之完全冪等性。
- **FR-011**: 解鎖事件發生時，系統 MUST 向 `raw_tracking_logs`（M0.4）寫入結構化稽核事件，包含 `module="M4.12"`、`achievement_id`、`trigger_archetype`、`confidence_score` 與耗時。
- **FR-012**: 系統 MUST 實作防刷與反向工程防護機制：單一使用者在冷卻時間內（如 60 秒）重複嘗試相同語意模式不重複計算，且單一隱藏成就終身僅可解鎖一次。
- **FR-013**: 前端接收到 `HIDDEN_ACHIEVEMENT_UNLOCKED` 事件後，系統 MUST 依序排入展示佇列，確保動畫流暢、特效等級與稀有度匹配，且支援無障礙鍵盤關閉。
- **FR-014**: 系統 MUST 實作全域使用者層級的隱藏成就作用域（Global User Scope）：所有隱藏成就歸屬於全域 `user_id`，並於 `UserAchievementRecord` 標記觸發當前之 `origin_role_id`；成就解鎖後於全域成就牆可見，終身不重複解鎖，且跨領域融合原型（`THE_POLYGLOT_SYNTHESIZER`）可跨多角色上下文綜合評估 [Clarification Session 2026-10-20 Q5]。
- **FR-015**: 系統 MUST 實作離線/斷線積壓成就之開機補發控制（Reconnect Catch-Up with Single Cap）：若客戶端重新連線或啟動時偵測到多筆未確認（`is_acknowledged = false`）之隱藏成就，最多僅以 `SurpriseModal` 展示 1 筆最高稀有度項目，並將其標記為已確認；其餘項目靜默標記已確認並於成就總覽點亮，附帶「NEW」視覺標籤，杜絕開機連續彈窗轟炸 [Clarification Session 2026-10-20 Q6]。

---

### Key Entities *(include if feature involves data)*

- **HiddenAchievementDefinition (隱藏成就定義實體)**:
  - `achievement_id`: 唯一識別碼（如 `ha_curious_cartographer_01`）。
  - `archetype`: 成長原型分類（`curiosity`, `metacognition`, `restoration`, `cross_synthesis`）。
  - `name`: 解鎖後顯示之成就名稱。
  - `description`: 解鎖後顯示之詳細探索描述。
  - `flavor_text`: 心理共鳴文案與啟發性金句。
  - `rarity`: 稀有度等級（`Rare`, `Epic`, `Legendary`）。
  - `exp_reward`: 經驗值激勵額度。
  - `badge_icon_url`: 徽章視覺資源路徑。
  - `eval_rules`: 宣告式驗證條件（概念跨度閾值、關鍵意圖維度、上下文要求）。
  - `is_hidden`: 永遠為 `true`。

- **EpistemicEvidence (探索特徵佐證實體)**:
  - `session_id` / `transcript_id`: 來源對話或反思記錄標識。
  - `concept_leap_depth`: 概念跳躍深度指標（相對於當前掌握度 BKT 差距）。
  - `proactivity_score`: 主動提問與探索權重分值（0.0 ~ 1.0）。
  - `extracted_themes`: 提取之高階主題概念標籤。
  - `detected_at`: 特徵捕捉時間戳。

- **UserAchievementRecord (使用者成就達成記錄)**:
  - `user_id`: 使用者唯一識別碼。
  - `achievement_id`: 成就識別碼。
  - `origin_role_id`: 觸發解鎖當下之作用角色識別碼（可為空，用於脈絡追溯）。
  - `unlocked_at`: 解鎖時間戳。
  - `is_acknowledged`: 是否已向使用者展示過驚喜彈窗並確認（布林值）。
  - `xp_awarded`: 實際發放 XP。
  - `transaction_id`: M6.5 ACID 交易流水號。
  - `context_summary`: 解鎖當下之觸發脈絡摘要（供日後回顧，去識別化）。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001 (絕對零 UI 與資料洩漏)**:
  未解鎖狀態下，針對客戶端 DOM 檢查與 API Payload 審查，隱藏成就資料外洩率為 0%（無字串、無 ID、無佔位節點、無剩餘計數洩漏）。
- **SC-002 (驗證準確率與偽陽性防護)**:
  在標準評測測試集（包含主動深探、隨機術語灌水、被動回答三種情境）下，主動探索特徵捕捉準確率 $\ge 90\%$，惡意/隨機關鍵字灌水偽陽性觸發率 $\le 2\%$。
- **SC-003 (解鎖端到端延遲)**:
  從特徵捕捉驗證通過、完成 M6.5 ACID 寫入，至 WebSocket 發布通知抵達桌面端，端到端耗時在正常狀態下 $\le 1.0$ 秒。
- **SC-004 (隱私三層合規性)**:
  隱藏成就特徵分析與評估過程 100% 在本機端完成，無任何 L1 原生對話文字洩漏至外部網路。
- **SC-005 (併發防重發放與冪等保證)**:
  在高併發重複觸發測試中，重送或連點情境下的重複解鎖與雙重給獎率為 0%。
- **SC-006 (心流與心理安全防護)**:
  當 M4.8 輸出標記處於焦慮或高負荷狀態時，干擾性全螢幕彈窗打斷率為 0%（延遲至中性微斷點呈現）。

---

## Assumptions

- **本機端推論能力**: 假設使用者桌面端已具備 M2.2 Gemma 本地推論或高效能輕量語意比對能力，能支援對話特徵提取與語意相似度計算。
- **通訊架構**: 假設桌面端（React / Tauri）與後端服務（FastAPI）之間具備穩定的本機 WebSocket 或 SSE 雙向長連線通道。
- **資料庫基底**: 假設 M6.1（SQLite）、M6.2/M6.3 與 M6.5（ACID Gatekeeper）之交易機制已具備，能承接成就入庫與 XP 結算。
- **依賴邊界**: M4.12 為進階模組，遵循專案憲法 Principle V，其存在與否不破壞 MVP 核心會話與日報功能之獨立運作。
