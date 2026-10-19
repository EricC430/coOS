# Tasks: M4.11 動態邊界任務池與 ZPD 盲盒管線 (Dynamic ZPD Gacha Pipeline)

**Feature Branch**: `002-m4-11-zpd-pipeline`  
**Date**: 2026-10-19  
**Specification**: [spec.md](./spec.md) | **Implementation Plan**: [plan.md](./plan.md)  
**Status**: Ready for Implementation  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 建立後端模組目錄、共享型別與測試環境基礎設施

- [X] T001 建立後端模組目錄 `services/m4_11_zpd_pipeline/` 與專屬測試目錄 `testing/m4_11/`
- [X] T002 [P] 在 `services/m4_11_zpd_pipeline/__init__.py` 建立模組版本常數與對外導出介面
- [X] T003 [P] 在 `testing/m4_11/conftest.py` 配置 pytest 測試環境與 SQLite 記憶體資料庫共用 Fixture

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立資料表綱要、Pydantic DTO 與離線種子庫，作為所有使用者故事的前置依賴

**⚠️ CRITICAL**: 本階段完成前，不得開始任何 User Story 的業務開發

- [X] T004 於 `services/m4_11_zpd_pipeline/models.py` 實作 SQLAlchemy 資料庫模型：
  - `role_skill_mastery`：包含複合唯一鍵 `uq_role_skill UNIQUE(user_id, role_id, skill_domain)`，`p_mastery` REAL NOT NULL DEFAULT 0.30，`consecutive_successes` 與 `consecutive_failures`
  - `zpd_challenges`：包含主鍵 `id` VARCHAR(64)，`user_id`，`role_id`，`title`，`description`，`task_type`，`is_real_world`，`difficulty`，`skill_domain`，`estimated_minutes`，`xp_reward`，`status`，`zpd_zone`，`scaffolding_hints` TEXT，`expires_at` TIMESTAMP
- [X] T005 [P] 於 `services/m4_11_zpd_pipeline/schemas.py` 實作 Pydantic DTO：
  - 定義 `TaskType`、`TaskDifficulty`、`ChallengeStatus` 列舉
  - 定義 `ZPDChallengeDTO`、`DrawChallengeRequest`、`AcceptChallengeRequest`、`CompleteChallengeRequest`
- [X] T006 [P] 於 `services/m4_11_zpd_pipeline/seeds.json` 建立預載離線種子題庫，涵蓋技術延伸題（如 Docker/Rust/Web）與生活恢復題（散步/料理/探店）
- [X] T007 於 `services/m4_11_zpd_pipeline/router.py` 建立 FastAPI 路由骨架並配置依賴注入
- [X] T008 於 `services/main.py` 註冊 `m4_11_router` 於 `/api/m4_11` 路徑下

**Checkpoint**: 基礎設施就緒，資料表與 API 骨架已連通，可開始並行開發各 User Story

---

## Phase 3: User Story 1 - 抽取符合當前能力邊界（ZPD）的動態延伸挑戰 (Priority: P1) 🎯 MVP

**Goal**: 實作動態挑戰抽取主流程，串接 M3.11.2 前端按鈕，落實零質押（Zero-Staking, RISK-07）與單一活躍槽位管理

**Independent Test**: 發送 `POST /api/m4_11/draw_challenge` 成功取得符合 ZPD 邊界之挑戰物件，並驗證無任何扣款/質押欄位

### Tests for User Story 1 (TDD Mandatory) ⚠️
- [X] T009 [P] [US1] 於 `testing/m4_11/test_draw_challenge_contract.py` 撰寫 `POST /api/m4_11/draw_challenge` 與 `openapi.yaml` 契約符合性測試
- [X] T010 [P] [US1] 於 `testing/m4_11/test_zero_staking.py` 撰寫零質押防護測試，驗證失敗/逾期扣款額度絕對為 0 [RISK-07]

### Implementation for User Story 1
- [X] T011 [US1] 於 `services/m4_11_zpd_pipeline/task_synthesizer.py` 實作種子槽位填充降級合成器，自 `seeds.json` 組裝挑戰物件
- [X] T012 [US1] 於 `services/m4_11_zpd_pipeline/service.py` 實作單一進行中槽位管理邏輯（查詢、建立、替換舊挑戰為 `abandoned`）
- [X] T013 [US1] 於 `services/m4_11_zpd_pipeline/router.py` 實作 `POST /api/m4_11/draw_challenge` 與 `POST /api/m4_11/accept_challenge` 處理函式
- [X] T014 [US1] 於 `services/m4_11_zpd_pipeline/rate_limiter.py` 實作滑動視窗防成癮冷卻機制（1 小時內抽取 $\ge 5$ 次回傳 429 及剩餘秒數）
- [X] T015 [US1] 於 `services/m4_11_zpd_pipeline/telemetry.py` 實作 `[R01]` 結構化日誌發送邏輯，將抽卡與接受事件發布至 `raw_tracking_logs`

**Checkpoint**: User Story 1 獨立可用，前端點擊「🎲 抽挑戰」可順利抽取並接受零風險任務

---

## Phase 4: User Story 2 - 歷史脈絡興趣與成長痛點動態探勘 (M4.11.1) (Priority: P2)

**Goal**: 非同步分析本地對話紀錄，精準萃取「延伸興趣點」與「卡關痛點」，注入生成提示詞

**Independent Test**: 模擬注入卡關對話，驗證萃取出之關鍵字能精準反映在挑戰標題與提示指針中，全程無 L1 明文上雲

### Tests for User Story 2 (TDD Mandatory) ⚠️
- [X] T016 [P] [US2] 於 `testing/m4_11/test_interest_extractor.py` 撰寫對話文字探勘與痛點標籤萃取之單元測試

### Implementation for User Story 2
- [X] T017 [US2] 於 `services/m4_11_zpd_pipeline/interest_extractor.py` 實作 `InterestExtractor`，從 SQLite `chat_transcripts` 讀取近 24 小時紀錄並萃取 `interest_topic` 與 `friction_point`
- [X] T018 [US2] 於 `services/m4_11_zpd_pipeline/interest_extractor.py` 實作新角色冷啟動降級邏輯（歷史為空時套用領域預設主題）
- [X] T019 [US2] 於 `services/m4_11_zpd_pipeline/task_synthesizer.py` 整合興趣與痛點標籤至 LLM Prompt 語境變數中

**Checkpoint**: User Story 1 + 2 連通，抽卡任務緊密呼應最近對話內容

---

## Phase 5: User Story 3 - 多模態 BKT 認知負荷推斷與 ZONE 邊界動態調節 (M4.11.2 & M4.11.3) (Priority: P3)

**Goal**: 實作多模態 BKT 數學模型與 ZONE 框架 REJECT + GRAD 演算法，提供焦慮安全退縮

**Independent Test**: 驗證掌握度 $P(L_t)$ 隨成功/逾期正確推演，且 M4.8 焦慮狀態下強制觸發安全退縮（時長 $\le 15$ 分鐘）

### Tests for User Story 3 (TDD Mandatory) ⚠️
- [X] T020 [P] [US3] 於 `testing/m4_11/test_bkt_tracker.py` 撰寫多模態 BKT 貝氏更新與掌握度區間映射測試
- [X] T021 [P] [US3] 於 `testing/m4_11/test_zone_sampler.py` 撰寫 ZONE REJECT + GRAD 階梯篩選與安全退縮邏輯測試

### Implementation for User Story 3
- [X] T022 [US3] 於 `services/m4_11_zpd_pipeline/bkt_tracker.py` 實作 `BKTTracker` 類別，維護 $P(L_0), P(T), P(G), P(S)$ 運算及 $zpd_{lower}, zpd_{upper}$ 區間計算
- [X] T023 [US3] 於 `services/m4_11_zpd_pipeline/zone_sampler.py` 實作 `ZoneSampler`，依照 `comfort`, `just-manageable`, `stretch` 難度階梯執行抽樣
- [X] T024 [US3] 於 `services/m4_11_zpd_pipeline/zone_sampler.py` 實作 M4.8 焦慮/高負荷門禁安全退縮：將難度鎖定在 `just-manageable` 下限，時長上限限制在 15 分鐘以內 [RISK-09]

**Checkpoint**: User Stories 1~3 連通，任務難度隨使用者能力與心理狀態動態自我調節

---

## Phase 6: User Story 4 - 挑戰完成、反思沉澱與 M6.5 ACID XP 派發 (Priority: P4)

**Goal**: 實作自我申報反思驗核，並經由 M6.5 ACID 交易原子寫入 XP 帳本，支援軟性自然過期

**Independent Test**: 送出非空反思成功觸發 M6.5 發放 XP，未填寫反思時拒絕發放；逾期時 0 XP 扣除

### Tests for User Story 4 (TDD Mandatory) ⚠️
- [X] T025 [P] [US4] 於 `testing/m4_11/test_complete_challenge.py` 撰寫反思欄位檢核、M6.5 ACID 派發與軟性過期整合測試

### Implementation for User Story 4
- [X] T026 [US4] 於 `services/m4_11_zpd_pipeline/router.py` 實作 `POST /api/m4_11/complete_challenge` 端點，嚴格驗證 `user_feeling` 與 `user_action_plan` 非空
- [X] T027 [US4] 於 `services/m4_11_zpd_pipeline/service.py` 串接 M6.5 `XPGatekeeper`，以原子交易發放激勵 XP 並更新 lifetime XP
- [X] T028 [US4] 於 `services/m4_11_zpd_pipeline/service.py` 實作軟性自然過期結轉邏輯（跨日 04:00 AM 或 24 小時後自動轉為 `expired`，XP 扣除為 0）

**Checkpoint**: User Stories 1~4 形成閉環，從抽挑戰、做挑戰到反思結算 XP 完整接通

---

## Phase 7: User Story 5 - 抽中框架外生活恢復任務與意料之外的機緣驚喜 (Priority: P5) 🍃 心理恢復

**Goal**: 結合注意力恢復理論（ART），引入散步、烹飪、探店等實體生活微冒險，並實作疲勞自適應權重提升

**Independent Test**: 驗證平時生活任務出現機率為 15%~20%，高負荷/疲勞時自適應躍升至 50%~80%

### Tests for User Story 5 (TDD Mandatory) ⚠️
- [X] T029 [P] [US5] 於 `testing/m4_11/test_restorative_serendipity.py` 撰寫機緣驚喜卡 15% 抽樣與疲勞自適應躍升至 50%~80% 之機率分佈測試

### Implementation for User Story 5
- [X] T030 [US5] 於 `services/m4_11_zpd_pipeline/zone_sampler.py` 實作雙軌抽樣矩陣與疲勞狀態權重提升演算法
- [X] T031 [US5] 於 `services/m4_11_zpd_pipeline/seeds.json` 補充 15 款實體世界生活微探險題庫（散步放空、料理新菜、微探店、感官覺察）
- [X] T032 [US5] 於 `services/m4_11_zpd_pipeline/task_synthesizer.py` 實作生活恢復型 Prompt 範本，強制標記 `is_real_world: true` 且預估時長 $\le 20$ 分鐘

**Checkpoint**: 完整達成全人身心平衡，生活微冒險與技術挑戰雙軌平滑運作

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 端到端全鏈路走查、性能驗證與隱私合規盤點

- [X] T033 [P] 執行 `specs/002-m4-11-zpd-pipeline/quickstart.md` 規劃之 4 大端到端手動情境驗收
- [X] T034 [P] 執行 L1 隱私審計，確認全流程日誌與掌握度無任何明文洩漏至雲端
- [X] T035 [P] 驗證前端組件 `apps/desktop/src/components/m3_11_gacha/DrawChallengeButton/index.tsx` 與 M4.11 回傳 DTO 之完整相容性
- [X] T036 執行後端全測試套件 `pytest testing/m4_11/`，確認 100% 通過（0 失敗）

---

## Dependencies & Execution Order

### Phase Dependencies
* **Phase 1 (Setup)**: 無依賴，立即可啟動。
* **Phase 2 (Foundational)**: 依賴 Phase 1，**阻擋所有 User Stories**。
* **Phase 3~7 (User Stories)**: 均依賴 Phase 2。
  * US1 (P1) 為核心 MVP，建議優先實作。
  * US2~US5 在 Phase 2 完成後可依序遞增或並行開發。
* **Phase 8 (Polish)**: 依賴所有期望上線之 User Stories 完成。

### User Story Dependencies
* **US1 (P1 抽卡核心)**: 依賴 Phase 2，可獨立驗收（MVP）。
* **US2 (P2 興趣探勘)**: 依賴 Phase 2，增強 US1 之 Prompt 語境。
* **US3 (P3 BKT/ZONE)**: 依賴 Phase 2，為 US1 提供數學邊界調節。
* **US4 (P4 反思/XP)**: 依賴 US1（需有挑戰實體），串接 M6.5。
* **US5 (P5 生活恢復)**: 依賴 US1 與 US3（基於 ZONE 權重切換）。

---

## Parallel Execution Opportunities

```bash
# Phase 1 并行任務
Task: T002 "services/m4_11_zpd_pipeline/__init__.py"
Task: T003 "testing/m4_11/conftest.py"

# Phase 2 并行任務
Task: T005 "services/m4_11_zpd_pipeline/schemas.py"
Task: T006 "services/m4_11_zpd_pipeline/seeds.json"

# 各 User Story 內部測試先寫 (TDD 并行)
Task: T009 "testing/m4_11/test_draw_challenge_contract.py"
Task: T010 "testing/m4_11/test_zero_staking.py"
Task: T016 "testing/m4_11/test_interest_extractor.py"
Task: T020 "testing/m4_11/test_bkt_tracker.py"
Task: T021 "testing/m4_11/test_zone_sampler.py"
Task: T025 "testing/m4_11/test_complete_challenge.py"
Task: T029 "testing/m4_11/test_restorative_serendipity.py"
```

---

## Implementation Strategy & MVP

1. **第 1 里程碑（MVP）**：完成 Phase 1 + Phase 2 + Phase 3 (US1)。此時前端即可真正呼叫後端 API 抽取離線種子挑戰，實現「🎲 抽挑戰」端到端連通。
2. **第 2 里程碑（心流與反思閉環）**：完成 Phase 5 (US3 BKT/ZONE) + Phase 6 (US4 反思結算)。閉環能力邊界與 XP 激勵。
3. **第 3 里程碑（個性化與全人平衡）**：完成 Phase 4 (US2 對話探勘) + Phase 7 (US5 生活恢復) + Phase 8 (Polish)。達到頂級個性化與身心韌性守護。
