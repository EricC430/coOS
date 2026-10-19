# Implementation Tasks: M3.11 遊戲化抽卡與視覺合成模組 (Gamification Gacha & Visual Studio)

**Branch**: `001-m3-11-gacha-ui` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data Model**: [data-model.md](./data-model.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 初始化 M3.11 組件目錄、型別系統與預設素材庫

- [X] T001 建立組件目錄結構 `apps/desktop/src/components/m3_11_gacha/` 及其子模組目錄
- [X] T002 建立型別定義檔案 `apps/desktop/src/components/m3_11_gacha/types.ts`（包含 `VisualItem`, `CanvasLayer`, `CanvasState`, `DrawRateLimitState`, `GachaPoolMode`, `HarmonizeRequest`, `HarmonizeResult`, `CustomThemeScene`, `ImplicitUserState`）
- [X] T003 [P] 建立預設素材庫與測試 Mock：
  - `presetBackgrounds.ts`（內建 6 款風格高清背景，支援離線與即時備援）
  - `presetObjects.ts`（內建 12 款具備透明 Alpha 通道之物件/徽章圖示）
  - `__tests__/mocks.ts`（API、免費圖生圖端點與 WebSocket Mock 工具）

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 現代自然語言句式重構與畫布雙軌合成核心 Hook

- [X] T004 [P] 實作現代自然語言 Prompt 構建模組 `apps/desktop/src/components/m3_11_gacha/promptBuilder.ts`（FLUX/SDXL 連貫句式重構，嚴禁碎片標籤堆疊）
- [X] T005 [P] 實作 HTML5 Canvas 圖片底稿合成 Hook `apps/desktop/src/components/m3_11_gacha/VisualStudioCanvas/useCanvasCompositor.ts`（雙緩衝圖層繪製、Alpha 混合抗鋸齒、SVG/Data URL 匯出）
- [X] T006 實作免金鑰免費圖生圖客戶端與降級 Hook `apps/desktop/src/components/m3_11_gacha/VisualStudioCanvas/useImageHarmonizer.ts`（呼叫 Pollinations/HuggingFace 免費端點，網路失敗或超時 10s 自動降級為 2D 畫布影像）

**Checkpoint**: 基礎架構就緒，各 User Story 可依序進行獨立驗收與整合

---

## Phase 3: User Story 1 - XP 盲盒抽獎與開獎系統 (Priority: P1) 🎯 MVP

**Goal**: 實作變動比例盲盒抽獎按鈕，具備 L1 即時 Toast、60 分鐘 5 次滑動視窗防沉迷冷卻，以及官方/混合獎池切換

**Independent Test**: `apps/desktop/src/components/m3_11_gacha/__tests__/gacha_ui.test.tsx` (驗證扣除 100 XP、即時開獎 Toast、5 次冷卻鎖定、自創作品入池抽取)

- [X] T007 [P] [US1] 撰寫 US1 抽獎驗收測試於 `apps/desktop/src/components/m3_11_gacha/__tests__/gacha_ui.test.tsx`
- [X] T008 [P] [US1] 實作滑動時間視窗頻率限制 Hook `apps/desktop/src/components/m3_11_gacha/GachaDrawButton/useDrawRateLimit.ts`（60 分鐘內最多 5 次抽獎，計算剩餘冷卻時間與抽獎次數，管理獎池模式）
- [X] T009 [P] [US1] 實作開獎 Toast 元件 `apps/desktop/src/components/m3_11_gacha/GachaDrawButton/GachaResultToast.tsx`（即時顯示、支援 Common / Rare / Epic / Legendary 稀有度光效、標註 `deferStrategy: "immediate"`）
- [X] T010 [US1] 實作盲盒抽獎按鈕主元件 `apps/desktop/src/components/m3_11_gacha/GachaDrawButton/index.tsx`（檢查 XP 餘額、連線抽獎端點、支援官方/自創混合獎池模式、觸發即時 Toast、整合冷卻提示與獎勵入庫）

**Checkpoint**: User Story 1 完整可獨立運作，通過 100% 驗收測試

---

## Phase 4: User Story 2 - 背景圖片生成功能 (Priority: P2)

**Goal**: 提供背景圖片生成介面，支援輸入「背景場景描述」與挑選風格模板，支援「投入抽獎池」選項

**Independent Test**: `apps/desktop/src/components/m3_11_gacha/__tests__/visual_generator.test.tsx` (背景生成依據場景描述、自然語言 Prompt 組合、勾選入池與錯誤重試)

- [X] T011 [P] [US2] 撰寫 US2 背景生成驗收測試於 `apps/desktop/src/components/m3_11_gacha/__tests__/visual_generator.test.tsx`
- [X] T012 [US2] 實作背景生成面板元件 `apps/desktop/src/components/m3_11_gacha/BackgroundGenerator/index.tsx`（場景描述輸入、風格模板選擇、生成 Loading 骨架屏、預覽與收藏庫儲存、「投入抽獎池」核取開關）

**Checkpoint**: User Story 1 與 User Story 2 均可獨立與整合運作

---

## Phase 5: User Story 3 - 物體與裝飾圖片生成功能 (Priority: P3)

**Goal**: 輸入「物件語意特徵」，生成具備透明背景（Alpha 通道）的獨立物體圖片，加入背包並可投入抽獎池

**Independent Test**: `apps/desktop/src/components/m3_11_gacha/__tests__/visual_generator.test.tsx` (物件生成去背句式、棋盤格透明校驗、背包儲存與入池)

- [X] T013 [P] [US3] 撰寫 US3 物件生成驗收測試於 `apps/desktop/src/components/m3_11_gacha/__tests__/visual_generator.test.tsx`
- [X] T014 [US3] 實作物件生成面板元件 `apps/desktop/src/components/m3_11_gacha/ObjectGenerator/index.tsx`（語意特徵輸入、透明度校驗棋盤格預覽、物體分類選取、「投入抽獎池」標記、生成結果加入背包）

**Checkpoint**: 獨立背景與獨立物體均已完成生成管線，支援自由擴充獎池

---

## Phase 6: User Story 4 - 畫布排版與「放置」AI 圖生圖融合 (Priority: P4) 🎨 核心視覺

**Goal**: 提供互動式畫布編輯器，支援底圖載入、物件排版底稿，點擊「放置」進行非破壞性 AI 融合與 2D 降級

**Independent Test**: `apps/desktop/src/components/m3_11_gacha/__tests__/canvas_editor.test.tsx` (排版圖層、點擊「放置」AI 融合、非破壞性圖層保留、2D 畫布降級與主題套用)

- [X] T015 [P] [US4] 撰寫 US4 畫布排版與融合測試於 `apps/desktop/src/components/m3_11_gacha/__tests__/canvas_editor.test.tsx`
- [X] T016 [P] [US4] 實作互動式畫布視圖 `apps/desktop/src/components/m3_11_gacha/VisualStudioCanvas/CanvasViewport.tsx`（底圖呈現、滑鼠與觸控事件拖曳物體、控制點縮放與旋轉）
- [X] T017 [P] [US4] 實作圖層控制面板 `apps/desktop/src/components/m3_11_gacha/VisualStudioCanvas/LayerControls.tsx`（圖層清單、坐標 X/Y、縮放與旋轉微調輸入、背包物件新增至畫布）
- [X] T018 [US4] 實作主畫布容器 `apps/desktop/src/components/m3_11_gacha/VisualStudioCanvas/index.tsx`（「✨ 放置（AI 融合）」按鈕、非破壞性成果預覽、返回編輯圖層按鈕、套用為主題保存 `CustomThemeScene`、PNG/WebP 下載）

**Checkpoint**: 畫布合成、AI 融合與 2D 雙軌降級全部就緒

---

## Phase 7: User Story 5 - 隱藏成就零洩漏、無預警驚喜彈窗與門禁 (Priority: P5) 🛡️ 心理約束

**Goal**: 整合原 SPEC 心理防護機制：未解鎖隱藏成就 0 洩漏、WebSocket 驚喜彈窗佇列、焦慮狀態推播抑制

**Independent Test**: `apps/desktop/src/components/m3_11_gacha/__tests__/gacha_ui.test.tsx` (隱藏成就零問號節點、驚喜彈窗 FIFO 佇列、焦慮情緒橫幅不渲染、動態 ZPD 任務無 XP 質押)

- [X] T019 [P] [US5] 撰寫 US5 心理機制驗收測試於 `apps/desktop/src/components/m3_11_gacha/__tests__/gacha_ui.test.tsx`
- [X] T020 [P] [US5] 實作成就網格過濾器 `apps/desktop/src/components/m3_11_gacha/HiddenAchievement/AchievementGrid.tsx`（未解鎖之隱藏成就 `hidden: true && !unlocked_at` 100% 不渲染）
- [X] T021 [P] [US5] 實作驚喜彈窗與排隊佇列 `apps/desktop/src/components/m3_11_gacha/HiddenAchievement/SurpriseModal.tsx` 與 `HiddenAchievementListener.tsx`（WebSocket 廣播監聽、FIFO 佇列依序彈出）
- [X] T022 [P] [US5] 實作主動促銷橫幅門禁 `apps/desktop/src/components/m3_11_gacha/GachaPromotion/index.tsx`（隱性狀態為焦慮/逃避/沮喪時返回 null）
- [X] T023 [US5] 實作抽挑戰按鈕 `apps/desktop/src/components/m3_11_gacha/DrawChallengeButton/index.tsx`（抽取 M4.11 ZPD 挑戰任務，介面嚴格無 XP 質押選項）

**Checkpoint**: 心理健康不變式與防沉迷門禁 100% 嚴格合規

---

## Phase 8: Integration, Telemetry & Polish (模組總匯出與遙測)

**Purpose**: 統一模組入口、串接事件遙測與全套回歸測試

- [X] T024 [P] 實作 M0.4 `raw_tracking_logs` 事件遙測函式 `apps/desktop/src/components/m3_11_gacha/telemetry.ts`
- [X] T025 [P] 撰寫遙測測試 `apps/desktop/src/components/m3_11_gacha/__tests__/telemetry.test.ts`
- [X] T026 建立模組總匯出入口 `apps/desktop/src/components/m3_11_gacha/index.ts`
- [X] T027 執行全套 Vitest 驗收測試與全域回歸測試，驗證 100% 綠燈並附上完整測試數據證據

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 無前置依賴，初始化型別與預設資產庫
- **Foundational (Phase 2)**: 依賴 Phase 1 完成，構建 PromptBuilder 與 Canvas Compositor
- **User Stories (Phase 3 ~ Phase 7)**:
  - **US1 (Phase 3, P1)**: 依賴 Foundational 完成，經濟抽獎與開獎系統，為 MVP 核心
  - **US2 (Phase 4, P2)**: 依賴 Foundational 完成，背景生成器
  - **US3 (Phase 5, P3)**: 依賴 Foundational 完成，物體生成器
  - **US4 (Phase 6, P4)**: 依賴 US2、US3 產出之資產結構，進行畫布排版與 AI 放置融合
  - **US5 (Phase 7, P5)**: 依賴 US1 完成，實作隱藏成就、驚喜彈窗與焦慮門禁
- **Polish (Phase 8)**: 依賴各 User Stories 完成，統一模組入口與遙測日誌

### Parallel Opportunities

- Phase 1: `T003` 預設背景與物件庫可與型別定義平行處理
- Phase 2: `T004` (PromptBuilder) 與 `T005` (Canvas Compositor) 可平行開發
- Phase 3: `T007` (測試) 與 `T008` (useDrawRateLimit)、`T009` (Toast) 可平行編寫
- Phase 6: `T016` (CanvasViewport) 與 `T017` (LayerControls) 可平行編寫
- Phase 7: `T020` (AchievementGrid)、`T021` (SurpriseModal)、`T022` (GachaPromotion) 可平行開發

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. 完成 Phase 1 Setup 與 Phase 2 Foundational
2. 完成 Phase 3 User Story 1 (XP 盲盒抽獎 + L1 即時開獎 Toast + 60 分鐘 5 次防沉迷)
3. 驗證 US1 獨立測試通過，即可交付最小可行版本

### Incremental Delivery
1. Setup + Foundational → 基礎建設就緒
2. 加入 US1 → 盲盒抽獎與開獎可用（MVP!）
3. 加入 US2 & US3 → 自訂背景與透明物體生成可用
4. 加入 US4 → 畫布即時排版、「放置」AI 融合、2D 備援與主題庫可用
5. 加入 US5 → 隱藏成就零洩漏、驚喜彈窗佇列、焦慮門禁與無質押 ZPD 挑戰
6. 模組統一匯出與 L1 raw_tracking_logs 遙測整合
