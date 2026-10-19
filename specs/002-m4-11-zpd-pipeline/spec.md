# Feature Specification: M4.11 動態邊界任務池與 ZPD 盲盒管線 (Dynamic ZPD Gacha Pipeline)

**Feature Branch**: `002-m4-11-zpd-pipeline`

**Created**: 2026-10-19

**Status**: Draft

**Input**: User description: "/speckit-constitution /speckit-specify  釐清M4.11功能設計"

## Clarifications

### Session 2026-10-19
- Q: 使用者執行 ZPD 挑戰任務時，系統應如何判定該任務已完成並解鎖反思與經驗值發放？ → A: 自我申報與反思驗證（Self-attestation via Reflection）：使用者主動點擊完成並填寫真實反思（`user_feeling` 與 `user_action_plan`），經 M6.5 XPGatekeeper 檢驗非空後核發 XP，不強制代碼自動審查，遵循專案憲法核心心理機制。
- Q: 進行中的 ZPD 挑戰任務應具備何種時效限制與逾期判定規則？ → A: 軟性自然過期（Soft Expiration at Day-End / 24h）：不設分秒緊迫倒數（防範時間壓迫感與焦慮），預設於每日跨日結算（04:00 AM 或發起後 24 小時）自動平滑結轉為過期，逾期不扣除任何 XP，使用者可隨時自主手動放棄或替換。
- Q: 全 LLM 動態生成挑戰任務時，系統在網路離線或推論超時（>5 秒）情況下的具體備援策略為何？ → A: 雙階降級備援（Dual-Tier Fallback）：優先嘗試本機 Gemma (M2.2)；若本機模型未啟用且雲端連線超時/離線（>5 秒），自動平滑降級為「領域預載種子庫 + 參數化組合（Curated Seeds + Slot Filling）」，保證 100% 離線可用且在 300ms 內返回任務。
- Q: 當對話興趣/痛點與認知負荷/BKT能力邊界發生衝突時，任務內容綜合生成應以何者為絕對約束？ → A: 安全邊界絕對優先（BKT & Cognitive Load Hard Gate）：認知負荷與 BKT 作為硬性天花板，將高難度興趣主題強制拆解為「符合當前能力與負荷的最小實作切片」（如 15 分鐘微任務），確保 100% 落在 ZPD 內，不因主題深奧而引發挫敗棄用。
- Q: 「框架外生活與恢復型任務」（如散步、煮菜、探店）在任務池中的觸發機制與出現時機應如何設計？ → A: 雙軌並進 + 疲勞自適應權重（Dual-Track with Fatigue-Adaptive Boost）：平時作為變動比例的「機緣驚喜卡（Serendipity Card）」（15%~20% 機率隨機掉落），帶來思維轉換；當 M4.8 偵測到高認知負荷或疲憊狀態時，系統自動將恢復型任務權重動態提升至 50%~80%，引導使用者藉由注意力恢復理論（ART）脫離螢幕走向真實生活。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 抽取符合當前能力邊界（ZPD）的動態延伸挑戰 (Priority: P1)

作為一名希望在專業或學習領域持續精進的使用者，我希望點擊「🎲 抽挑戰」時，系統能依據我近期的學習脈絡與能力前沿，動態生成一個「剛剛好有點挑戰、但又不至於挫敗崩潰」的隨機任務，並且絕無任何扣經驗值處罰的風險，讓我可以無心理負擔地探索成長。

**Why this priority**:
這是 M4.11 的核心業務價值與主流程閉環。直接串接前端 M3.11.2 的「🎲 抽挑戰」互動，將枯燥的進度管理轉化為具備「適度變動比例增強」的遊戲化體驗，是激發內在學習動機的關鍵。

**Independent Test**:
- 前端發起 `POST /api/m4_11/draw_challenge` 請求（攜帶 `role_id`），後端在 1.5 秒內回傳符合 `ZPDChallenge` 結構的任務物件。
- 驗證挑戰物件包含標題、具體描述、預估時間（15~45 分鐘）、`just-manageable` 或 `stretch` 難度標記，以及對應的正向 XP 獎勵值。
- 驗證該挑戰物件與後端接口中**完全不存在任何 XP 質押（Stake）、押金或扣款邏輯** [R01 §α-DPO, RISK-07, Constitution Principle II]。

**Acceptance Scenarios**:

1. **Given** 使用者處於一般或心流狀態，在特定角色（如 `role_csie`）下點擊「🎲 抽挑戰」，**When** M4.11 計算 ZPD 任務池，**Then** 回傳之挑戰難度落在當前使用者的近側發展區（成功機率介於 50% ~ 80%），並提供額外激勵 XP。
2. **Given** 使用者抽到 ZPD 挑戰任務，**When** 檢視任務細節與結算規則，**Then** 任務失敗或逾期僅標記為過期/未完成，**嚴禁扣除任何現有 XP**，杜絕複合挫敗引發的棄用危機 [RISK-07]。
3. **Given** 使用者連續抽卡達到冷卻上限（1 小時內 ≥ 5 次），**When** 嘗試再次請求，**Then** 系統回傳友善冷卻提示，防止賭徒式刷任務行為 [R09 §3.3]。

---

### User Story 2 - 歷史脈絡興趣與成長痛點動態探勘 (M4.11.1) (Priority: P2)

作為一名與 AI 助理持續對話的使用者，我希望抽到的挑戰任務能緊密貼合我剛才在對話中提到的專案痛點或延伸興趣（例如「Docker 網路隔離老是搞不懂」或「想嘗試 Rust 非同步程式設計」），而不是千篇一律的罐頭題庫。

**Why this priority**:
客製化與相關性是維持長期投入感的核心。若任務只是靜態題庫，使用者很快會失去新鮮感；透過 M4.6 Observer 背景監聽對話萃取關鍵痛點，能讓任務精準擊中學習熱點。

**Independent Test**:
- 在本地測試資料庫注入包含「Docker 網路連線 debug 耗時過長」的 `chat_transcripts`，觸發 M4.11.1 興趣分析器，驗證萃取出之關鍵字標籤（如 `docker_network`, `debug_friction`）被正確索引至任務生成候選集。
- 驗證分析過程 100% 在本地完成，無任何對話原文或個人識別資料上傳雲端（滿足 Constitution Principle I L1 隱私規範）。

**Acceptance Scenarios**:

1. **Given** 使用者在最近 24 小時內的對話記錄中提及特定主題的卡關或學習興趣，**When** M4.11.1 執行背景分析，**Then** 擷取出的主題關鍵字與痛點標籤被注入到候選任務生成管線中。
2. **Given** 新建立的角色或歷史對話為空（冷啟動情境），**When** 使用者發起抽挑戰，**Then** 系統自動平滑降級採用該角色預設的領域骨幹挑戰庫，確保無異常報錯。

---

### User Story 3 - 多模態 BKT 認知負荷推斷與 ZONE 邊界動態調節 (M4.11.2 & M4.11.3) (Priority: P3)

作為一名在不同日子與時段狀態起伏的使用者，我希望當我精神飽滿時能抽到更具挑戰性的硬核任務，而當我已經疲憊焦慮時，系統能自動收斂難度或暫緩高難度挑戰，避免落井下石。

**Why this priority**:
結合 R01 核心理論（多模態貝氏知識追蹤 BKT 與 ZONE 框架的 REJECT + GRAD 機制），提供動態難度調節（DDA）。

**Independent Test**:
- 模擬輸入高認知負荷與焦慮信號（M4.8 輸出 `label: "anxiety", confidence: 0.85`），驗證 M4.11 自動觸發 ZONE 安全退縮（Safety Retraction），剔除所有 `stretch` 等級任務，僅保留低負荷 `just-manageable` 微任務，並配合 M3.11 封鎖主動推播。
- 模擬連續成功完成任務的正面遙測數據，驗證 BKT 掌握度 $P(L_t)$ 漸進上升，動態提升 ZPD 下限與上限。

**Acceptance Scenarios**:

1. **Given** M4.8 傳入使用者當前處於 `anxiety` 或高認知負荷狀態，**When** 使用者主動點擊抽挑戰，**Then** 系統自動下調任務預估耗時至 15 分鐘以內，且難度限制在 `comfort` 至 `just-manageable` 邊界，給予修復自信的微成功體驗 [R01 §Dropout 危機管理]。
2. **Given** 候選任務池中存在低於使用者當前能力閾值的平庸任務與遠高於上限的超負荷任務，**When** ZONE 演算法執行篩選，**Then** `REJECT` 階段濾除過易與過難項目，`GRAD` 階段依階梯梯度在 ZPD 區間內進行機率抽樣。

---

### User Story 4 - 挑戰完成、反思沉澱與 M6.5 ACID XP 派發 (Priority: P4)

作為一名完成延伸挑戰的使用者，我希望在完成任務後能填寫簡短的心得與下一步行動，並獲得受資料庫嚴格保護的 XP 獎勵與里程碑記錄。

**Why this priority**:
維持專案憲法 Principle II 的「微摩擦（Micro-friction）」與「IKEA 效應」心理機制，確保成就感牢固建立在真實反思上，而非無意識點擊。

**Independent Test**:
- 提交完成挑戰請求（包含非空白之 `user_feeling` 與 `user_action_plan`），呼叫 M6.5 `XPGatekeeper`，驗證交易以 ACID 方式原子更新 `current_xp` 與 `lifetime_xp`。
- 驗證未填寫反思欄位時，XP 絕對不會提前發放。

**Acceptance Scenarios**:

1. **Given** 使用者完成一項已接受的 ZPD 挑戰，**When** 填寫完成反思並送出，**Then** M6.5 ACID 交易原子寫入 XP 帳本，並發布 `CHALLENGE_COMPLETED` 結構化事件至 `raw_tracking_logs`。
2. **Given** 使用者接受了挑戰但在時限內未完成，**When** 挑戰過期，**Then** 狀態轉為 `expired`，不扣除任何 XP，使用者可隨時重新抽取新挑戰。

---

### User Story 5 - 抽中框架外生活恢復任務與意料之外的機緣驚喜 (Priority: P5) 🍃 心理恢復

作為一名長時間沉浸在專注學習或燒腦工作中的使用者，我希望點擊抽挑戰時，除了專業技能任務，也能偶爾抽到打破思維框架的生活微冒險（例如「外出散步 20 分鐘觀察 3 種植物」、「為自己煮一道新菜」、「探索一間未曾去過的街角小店」），讓我有理由暫時放下螢幕、回到真實實體世界，恢復枯竭的認知精力與注意力。

**Why this priority**:
結合注意力恢復理論（Attention Restoration Theory, ART）與認知心理學的孵化效應（Incubation Effect）。長時間的高強度螢幕作業會導致定向注意力疲乏（Directed Attention Fatigue）；適度的「框架外實體生活探索」提供軟性著迷（Soft Fascination），是維持身心韌性、避免職業倦怠與誘發潛意識創造力的不可或缺設計。

**Independent Test**:
- 正常認知狀態下模擬連續抽取挑戰，驗證 `task_type: "restorative_serendipity"` 出現機率落於 15%~20% 區間。
- 傳入 M4.8 輸出之疲勞或高負荷信號（如 `directed_attention_fatigue: true` 或 `continuous_focus_minutes > 120`），驗證恢復型生活任務之動態抽樣權重提升至 50%~80%。
- 驗證生活恢復任務完成後填寫反思，同樣透過 M6.5 發放正向激勵 XP。

**Acceptance Scenarios**:

1. **Given** 使用者在日常狀態下點擊抽挑戰，**When** 隨機抽樣命中機緣驚喜機率（~15%），**Then** 系統回傳生活恢復型挑戰（如「出門漫步 20 分鐘並拍一張天空照片」），介面標示「🍃 機緣驚喜卡」，激發探索意願。
2. **Given** 系統偵測到使用者連續高度用腦且認知負荷居高不下，**When** 使用者發起抽挑戰，**Then** 系統自適應提升恢復型任務權重（50%~80%），溫和推薦散步、烹飪或感官放鬆等實體行動，引導使用者脫離螢幕。
3. **Given** 使用者完成實體生活探索任務，**When** 填寫體驗感受並送出反思，**Then** M6.5 正常核算並發放 XP，確認生活體驗與專業進步受到同等珍視。

---

### Edge Cases

- **焦慮高壓狀態下的挑戰抽取 (RISK-09)**：
  當 M4.8 標記當前情緒為焦慮或耗竭時，禁止系統發起任何主動式彈窗挑戰；若使用者手動開啟並點擊，強制切換為「信心修復模式（Confidence Rebuild）」，任務耗時不超過 10 分鐘，且提示文字強調輕鬆體驗。
- **冷啟動無對話與掌握度數據**：
  若新角色完全無對話歷史與 BKT 紀錄，BKT 初始先驗機率設為保守預設值 $P(L_0) = 0.3$，推薦入門級別的環境配置或觀念理解任務。
- **重複任務抽樣與疲乏防範**：
  過去 7 天內已完成或已放棄的同一任務題目，自候選池中暫時排除，確保任務的多樣性。
- **完全離線與超時降級能力**：
  當使用者處於無網路連線環境或雲端推論超時（>5 秒）時，系統自動啟動雙階降級備援，透過本地內建的領域精選種子庫與槽位填充參數化組合（Curated Seeds + Slot Filling）即時合成挑戰，保證 100% 離線可用且在 300 毫秒內返回任務 [Clarification Q3]。
- **跨角色切換狀態隔離 (RISK-06)**：
  切換 `role_id` 時，BKT 掌握度與 ZPD 區間立即切換至目標角色的獨立紀錄，嚴禁 CSIE 角色的程式設計掌握度溢出污染生活或設計角色的任務池。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系統 MUST 實作 `POST /api/m4_11/draw_challenge` 端點，接收 `role_id`，回傳符合當前 ZPD 區間之隨機客製化挑戰物件。
- **FR-002**: 系統 MUST 嚴格落實 **Zero-Staking 零質押鐵律**：ZPD 挑戰生成、接受與逾期結算之任何環節，絕對禁止要求或允許扣除現有 XP 質押，失敗或逾期扣款額度為 0 [Constitution Principle II, R01 §α-DPO, RISK-07]。
- **FR-003**: 系統 MUST 實作 M4.11.1 歷史脈絡興趣分析器，非同步讀取本地 SQLite 之 `chat_transcripts`，萃取痛點與延伸興趣關鍵字，全程不向外部發送未去識別化之明文內容 [Constitution Principle I]。
- **FR-004**: 系統 MUST 實作 M4.11.2 多模態 BKT 認知負荷推斷器，依據任務耗時、反思文字情緒及 M4.8 `CognitiveLoad` 信號，動態更新各領域技能掌握度機率 $P(L_t)$。
- **FR-005**: 系統 MUST 實作 M4.11.3 ZONE 框架演算法，採用 `REJECT` 機制濾除超界任務，並採用 `GRAD` 階梯梯度演算法在 ZPD 區間抽樣。
- **FR-006**: 當 M4.8 輸出隱性狀態包含 `anxiety`、`avoidance` 或認知負荷過載時，M4.11 MUST 啟動 **安全退縮（Safety Retraction）機制**，難度降級為 `just-manageable` 下限，並將任務時長上限壓縮至 15 分鐘以內 [RISK-09]。
- **FR-007**: 挑戰任務完成後之 XP 派發，MUST 委由 M6.5 `XPGatekeeper` 執行 ACID 交易，嚴格檢驗反思內容填寫，杜絕幽靈 XP 派發 [Constitution Principle II, M6.5]。
- **FR-008**: 系統 MUST 支援滑動視窗防成癮機制：單一使用者 1 小時內抽取挑戰超過 5 次時，回傳冷卻中狀態及剩餘冷卻時間。
- **FR-009**: 系統 MUST 在所有關鍵狀態流轉（抽卡、接受、完成、退縮、過期）時，向 M0.4 `raw_tracking_logs` 發送帶有 `[R01]` 標籤的結構化 Telemetry 事件。
- **FR-010**: 系統 MUST 採用**全 LLM 動態生成模式**生成候選挑戰，並實作**雙階降級備援機制（Dual-Tier Fallback）**：優先調用本機 Gemma (M2.2) 進行情境推論；若本機模型未啟用且雲端連線超時（>5 秒）或離線，自動平滑降級至「領域預載種子庫 + 參數化組合（Curated Seeds + Slot Filling）」，保證 100% 離線可用且在 300ms 內返回任務 [Decision: 全 LLM 動態生成 + 雙階降級備援, Clarification Q3]。
- **FR-011**: 系統 MUST 實作**單一活躍挑戰槽位（Single Active Challenge Slot）**：單一角色同時最多僅能啟動 1 個進行中 ZPD 挑戰。當使用者再次抽取到新挑戰時，介面與後端提供「替換目前挑戰」或「保留原挑戰」之明確二選一操作，杜絕未完成任務堆積產生的心理負擔 [Decision: 單一活躍挑戰槽位]。
- **FR-012**: 系統 MUST 實作**獨立 `role_skill_mastery` 資料表並預留 M5 圖譜整合（Hybrid Relational + Graph Ready）**：在本地 SQLite 建立獨立資料表，以 `(user_id, role_id, skill_domain)` 為複合鍵儲存 BKT 掌握度機率 $P(L_t)$ 與連續成功/挫敗統計；同時資料結構保留標準技能實體介面，為未來無縫橋接至 M5 薩提爾深層認知圖譜（GraphRAG）預留技能節點擴充規格 [Decision: 1+3 混合架構]。
- **FR-013**: 系統 MUST 採用**自我申報與反思驗證機制（Self-Attestation via Reflection）**進行挑戰驗收：不強制實作程式碼沙盒或自動批改邏輯，使用者完成挑戰後，在介面主動觸發完成，並填寫真實反思欄位（`user_feeling`, `user_action_plan`），由 M6.5 `XPGatekeeper` 驗證反思有效性後原子派發 XP [Constitution Principle II, Clarification Q1]。
- **FR-014**: 系統 MUST 實作**軟性自然過期機制（Soft Expiration at Day-End / 24h）**：進行中挑戰不設急迫的分秒倒數計時器，預設於每日跨日結算時（如 04:00 AM 或建立後 24 小時）自動平滑轉為 `expired` 狀態；逾期或放棄絕不扣除現有 XP，且使用者隨時可主動放棄或以新抽取的挑戰進行替換 [Constitution Principle II, Clarification Q2]。
- **FR-015**: 系統 MUST 實作**多維信號綜合生成階層（Synthesis Hierarchy & Constraint Ordering）**：任務生成 Prompt 以 BKT 掌握度與 M4.8 認知負荷為**硬性邊界天花板**，以 M4.11.1 對話痛點與延伸興趣為**語境主題**；當兩者跨度過大時，系統強制將深奧主題拆解為符合當前 ZPD 邊界的「最小可實作切片（Minimal Executable Slice）」，保證任務時長在 15~45 分鐘內且具備明確完成定義 [Clarification Session 2026-10-19 Q4]。
- **FR-016**: 系統 MUST 支援**框架外生活恢復任務（Restorative & Serendipity Tasks）**：任務池中納入非工作/非技術類之實體生活微探險（如散步放空、烹飪新菜、微探店、五感覺察）；平時以 15%~20% 變動機率作為機緣驚喜卡隨機掉落，當 M4.8 判定處於高認知負荷或持續疲勞時，系統自動將恢復型任務之抽樣權重自適應提升至 50%~80%，引導使用者透過注意力恢復理論（ART）脫離螢幕走向真實生活 [Clarification Session 2026-10-19 Q5]。

---

### Key Entities *(include if feature involves data)*

- **ZPDChallenge**:
  - `id`: 挑戰唯一標識符（UUID）
  - `role_id`: 所屬角色識別碼
  - `title`: 挑戰標題（如「實作 Docker 自訂 Bridge 網路並隔離容器」或「🍃 機緣：出門散步 20 分鐘並拍一張天空照片」）
  - `description`: 任務詳細說明與建議步驟
  - `task_type`: 任務類別（`skill_stretch` 專業技能延伸 | `restorative_serendipity` 框架外生活恢復）
  - `is_real_world`: 是否為脫離螢幕之實體世界行動（`boolean`）
  - `difficulty`: 難度等級（`just-manageable` | `stretch` | `restorative`）
  - `skill_domain`: 關聯技能領域（如 `infra`, `frontend`, `algorithm`, `life_restoration`）
  - `estimated_minutes`: 預估完成時長（15 ~ 45 分鐘）
  - `xp_reward`: 完成可獲得之經驗值獎勵（30 ~ 100 XP）
  - `status`: 任務生命週期狀態（`generated` | `accepted` | `completed` | `expired` | `abandoned`）
  - `zpd_zone`: 位於近側發展區之具體區段（`core_zpd` | `upper_stretch` | `restorative_haven`）
  - `scaffolding_hints`: 鷹架指針陣列（2~3 條思考引導或除錯/實踐方向，降低無助感）
  - `accepted_at`: 接受挑戰時間戳記（ISO 8601）
  - `expires_at`: 預計自然過期時間戳記（ISO 8601，建立後 24h 或次日 04:00 AM）

- **RoleSkillMastery (BKT Profile)**:
  - `role_id`: 角色 ID
  - `skill_domain`: 技能範疇標籤
  - `p_mastery`: 當前掌握度機率 $P(L_t) \in [0.0, 1.0]$
  - `consecutive_successes`: 連續成功次數
  - `consecutive_failures`: 連續挫敗次數
  - `last_attempt_at`: 最後挑戰時間戳記

- **ZPD 任務核心性質分類學 (Core Task Properties Taxonomy)**:
  1. **微閉環性（Micro-Closed Loop）**：嚴格限定 15~45 分鐘內可獨立驗收的最小實作切片，具有明確「完成定義（Definition of Done）」，絕非幾天幾週的模糊專案。
  2. **近側延展性（Proximal Scaffolding）**：難度嚴格落在 `[zpd_lower, zpd_upper]` 區間（預期成功率 50%~80%），附帶 2~3 項排錯思考指針（鷹架），杜絕無頭緒盲搜。
  3. **情境共鳴性（Contextual Resonance）**：錨定近 24 小時對話卡關痛點與延伸興趣，直擊真實學習熱點。
  4. **心理無害與無損性（Psychological Safety & Zero-Staking）**：零扣款、零罰則、軟性過期、自由替換，杜絕複合挫敗。
  5. **實體世界換位性（Real-world Serendipity & Sensory Grounding）**：突破數位螢幕框架，透過散步、料理、微探店等實體行動提供注意力恢復（ART）與潛意識孵化效應（Incubation Effect）。

- **多維信號綜合生成架構 (Multi-Signal Synthesis Pipeline)**:
  - **信號 1（主題語境）**：M4.11.1 / M4.6 Observer 擷取的近 24 小時 `interest_topic`（延伸興趣）與 `friction_point`（卡關痛點）。
  - **信號 2（硬性約束天花板與恢復調節）**：M4.11.2 BKT 掌握度 $P(L_t)$ 與 M4.8 `CognitiveLoad`，決定難度等級、時間上限與生活恢復任務權重（50%~80%）。
  - **信號 3（邊界隔離）**：M4.3 `RoleContext`，限定在當前角色領域，防止跨領域技能污染。
  - **信號 4（多樣性防疲乏）**：過去 7 天任務排他過濾器，確保任務類型與標題不重複。

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 抽取的 ZPD 挑戰任務，90% 以上的使用者自評反思認為難度「適中且具啟發性」，任務自然完成率落在 60% ~ 80% 的黃金心流區間。
- **SC-002**: 挑戰抽取介面端點 `POST /api/m4_11/draw_challenge` 的 P95 響應時間小於 1,500 毫秒（離線範本模式小於 300 毫秒）。
- **SC-003**: 零質押與心理防護達成率 100%：在任何情況下因 ZPD 挑戰失敗而導致 XP 扣除的意外案例數為 0 [RISK-07 零容忍]。
- **SC-004**: 焦慮狀態安全退縮響應率 100%：當 M4.8 發布焦慮信號時，後續抽取的任務 100% 限制在 `just-manageable` 輕量區間且時長 ≤ 15 分鐘。
- **SC-005**: 隱私合規性 100%：歷史對話探勘與 BKT 計算過程絕不將 L1 明文日誌送出本地機器。

---

## Assumptions

- **離線優先**: 本地環境具備 SQLite 資料庫與基礎 CPU 計算資源，能獨立執行 BKT 更新與範本匹配。
- **前端協同**: 前端 M3.11 已實作相容之 `DrawChallengeButton` 與展示卡片組件，能夠解析 `ZPDChallenge` 資料結構。
- **角色邊界明確**: 使用者處於已啟用的具體角色上下文下（`role_id` 有效），未指明角色時預設套用系統主要角色。
- **XP 結算統一入口**: 所有經驗值增減均必須通過 M6.5 `XPGatekeeper`，本模組僅提供核算好的合規激勵點數，不自行直接修改帳本底表。
