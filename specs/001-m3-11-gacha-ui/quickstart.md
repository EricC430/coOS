# Quickstart & Verification Guide: M3.11 Gamification Gacha & Visual Studio

## Overview

本指南說明如何獨立執行與驗證 M3.11 遊戲化抽卡與視覺合成模組的自動化驗收測試與互動走查。

---

## 1. 執行單元與組件整合測試

在專案根目錄下使用 `pnpm` 執行專屬測試套件：

```bash
# 執行 M3.11 全部 4 個測試套件（共 21 個測試案例）
pnpm --filter @coos/desktop test src/components/m3_11_gacha/__tests__

# 或單獨執行特定測試套件：
# 1. US1 & US5: 抽卡經濟、防沉迷冷卻、隱藏成就與心理門禁
pnpm --filter @coos/desktop test src/components/m3_11_gacha/__tests__/gacha_ui.test.tsx

# 2. US2 & US3: 背景生成、物體去背與獎池標記
pnpm --filter @coos/desktop test src/components/m3_11_gacha/__tests__/visual_generator.test.tsx

# 3. US4: 畫布排版、「放置」AI 融合、非破壞性圖層保留與 2D 降級
pnpm --filter @coos/desktop test src/components/m3_11_gacha/__tests__/canvas_editor.test.tsx

# 4. FR-015: 本地 L1 raw_tracking_logs 遙測記錄
pnpm --filter @coos/desktop test src/components/m3_11_gacha/__tests__/telemetry.test.ts
```

預期結果：**4 個測試套件全數 PASS，21 個測試案例 100% 綠燈**。

---

## 2. 驗收場景手動走查流程

1. **盲盒抽獎與開獎 (US1)**:
   - 開啟抽獎面板，顯示「單次抽獎: 100 XP」與目前 XP 餘額。
   - 點擊「盲盒抽獎」，立即彈出具備稀有度光效之 `GachaResultToast`（標註 `deferStrategy: "immediate"`）。
   - 支援切換「官方精選池」與「自創混合池」。
   - 連續抽獎達 5 次時，按鈕強制鎖定並提示 60 分鐘滑動冷卻剩餘時間。

2. **背景與物體生成 (US2, US3)**:
   - 開啟 `BackgroundGenerator`，輸入背景場景描述並選擇風格模板，系統重構為自然語言連續句式生成背景，支援勾選「投入抽獎池」。
   - 開啟 `ObjectGenerator`，輸入物件語意特徵，生成具備透明背景之獨立物體，支援棋盤格透空預覽校驗。

3. **畫布排版與「放置」AI 融合 (US4)**:
   - 載入背景並由背包加入裝飾物件。
   - 在畫布上自由位移、旋轉、縮放物體圖層。
   - 點擊「✨ 放置（AI 融合）」，呼叫免金鑰免費服務執行 Image-to-Image 圖生圖。
   - 融合預覽展示後，點擊「返回編輯圖層」，確認底層圖層資料 100% 完好無缺（非破壞性保留）。
   - 當網路斷線或逾時時，自動無縫降級為 2D 畫布合成圖，並顯示降級提示。
   - 點擊「套用為主題」，一鍵設定為 coOS 桌面背景主圖，並支援 PNG/WebP 下載。

4. **心理防護約束 (US5)**:
   - 未解鎖之隱藏成就於 `AchievementGrid` 中 0% 渲染（無問號佔位符、無空節點，防 FOMO）。
   - 收到 WebSocket 解鎖事件時，`SurpriseModal` 以 FIFO 佇列依序彈出。
   - 使用者處於焦慮/逃避狀態時，主動促銷橫幅 100% 抑制不渲染。
   - `DrawChallengeButton` 抽取 ZPD 任務，介面嚴格禁止 XP 質押。

