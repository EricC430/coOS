# Implementation Plan: M3.11 遊戲化抽卡與視覺合成模組 (Gamification Gacha & Visual Studio)

**Branch**: `001-m3-11-gacha-ui` | **Date**: 2026-10-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-m3-11-gacha-ui/spec.md` (經過 `/speckit-clarify` 澄清強化)

## Summary

本模組建構一套整合「資產分立生成」、「盲盒抽取」與「畫布排版 + AI 放置圖生圖融合」的個人化視覺系統：
1. **XP 盲盒抽獎系統**：變動比例抽取背景或獨立物件，具備 L1 即時 Toast（不經 M3.9 Defer 延遲）與 1 小時 5 次滑動視窗防沉迷冷卻 [R09 §3.3, RISK-04, RISK-09]。
2. **背景圖片生成器**：依據「背景場景描述」（Scene Prompt）與風格模板產出獨立背景底圖。
3. **物體圖片生成器**：依據「物件語意特徵」（Semantic Features）產出具備透明通道（Alpha Channel）的獨立物件、徽章與道具。
4. **畫布排版與「放置」AI 圖生圖融合**：
   - 使用者在背景之上即時排版、拖曳物體作為視覺底稿。
   - 點擊「放置」時呼叫免金鑰免費服務（如 Pollinations.ai / HuggingFace 免費端點）執行 Image-to-Image 圖生圖，融合背景與物件之光影、透視與材質。
   - 網路異常或超時時自動 100% 降級保留 2D 畫布成果，不中斷體驗。
5. **綜合原 SPEC 心理機制**：隱藏成就零 UI 洩漏（防 FOMO）、WebSocket 驚喜解鎖彈窗佇列、焦慮狀態促銷推播抑制門禁，以及無 XP 質押之 ZPD 抽挑戰按鈕。

---

## Technical Context

**Language/Version**: TypeScript 5.x / React 18  
**Primary Dependencies**: React, Tailwind CSS, `lucide-react`, HTML5 Canvas API, Vitest, React Testing Library  
**External Services**: 免費免金鑰 Image-to-Image 公共端點（Pollinations.ai / HuggingFace 免費推論 API）  
**Storage**: 本地記憶體/React State + LocalStorage（抽獎頻率滑動視窗與自訂合成場景快取）  
**Testing**: Vitest (`apps/desktop/src/components/m3_11_gacha/__tests__/`)  
**Target Platform**: Desktop App (Vite + React / Tauri)  
**Performance Goals**:
- 抽獎開獎 Toast 響應 < 100ms
- 畫布支援 ≥ 10 個物件圖層拖曳維持 60 FPS
- AI 圖生圖融合等待超時門檻 10s，超時 100% 無縫降級為 2D 畫布合成圖
- 隱藏成就 DOM 洩漏率 0%  
**Constraints**:
- L1 即時通道（不走斷點延遲）
- 防沉迷滑動視窗（1 小時最多 5 次）
- 免金鑰與零設定門檻（免費資源開箱即用）
- 心理狀態感知（焦慮隱性狀態下完全抑制主動推播）

---

## Project Structure

### Source Code Layout

```text
apps/desktop/src/components/m3_11_gacha/
├── types.ts                                    # 視覺資產、圖層、抽獎與 AI 融合型別定義
├── GachaDrawButton/                            # US1: XP 盲盒抽獎
│   ├── index.tsx                               # 抽獎按鈕主元件
│   ├── GachaResultToast.tsx                    # L1 即時開獎通知
│   └── useDrawRateLimit.ts                     # 滑動視窗連續冷卻 Hook
├── BackgroundGenerator/                        # US2: 背景圖片生成（場景描述）
│   ├── index.tsx                               # 背景生成面板
│   └── presetBackgrounds.ts                    # 內建精美背景庫（離線/預設備援）
├── ObjectGenerator/                            # US3: 物體圖片生成（語意特徵 + 透明通道）
│   ├── index.tsx                               # 物件生成面板
│   └── presetObjects.ts                        # 內建透明物件與徽章庫
├── VisualStudioCanvas/                         # US4: 畫布排版與「放置」AI 圖生圖融合
│   ├── index.tsx                               # 視覺工作室主容器
│   ├── CanvasViewport.tsx                      # 互動畫布視圖（底稿拖曳、縮放、旋轉）
│   ├── LayerControls.tsx                       # 圖層順序與屬性調整面板
│   ├── useCanvasCompositor.ts                  # HTML5 Canvas 2D 底稿截圖與合成
│   └── useImageHarmonizer.ts                   # 免金鑰免費服務（Pollinations/HF）圖生圖客戶端與 2D 降級處理
├── HiddenAchievement/                          # US5: 隱藏成就與驚喜控制
│   ├── AchievementGrid.tsx                     # 絕對無 UI 狀態網格過濾器
│   ├── HiddenAchievementListener.tsx           # WebSocket 事件監聽與彈窗佇列
│   └── SurpriseModal.tsx                       # 無預警驚喜解鎖彈窗
├── DrawChallengeButton/                        # US5: 程序化抽挑戰
│   ├── index.tsx                               # 抽挑戰按鈕（無質押）
│   └── ChallengeResultCard.tsx                 # ZPD 挑戰任務卡片
├── GachaPromotion/                             # US5: 焦慮狀態感知推播門禁
│   └── index.tsx                               # 焦慮/沮喪時返回 null
├── index.ts                                    # 模組總匯出入口
└── __tests__/                                  # TDD 驗收測試套件
    ├── gacha_ui.test.tsx                       # 抽獎與心理機制驗收測試
    ├── visual_generator.test.tsx               # 背景與物體生成測試
    ├── canvas_editor.test.tsx                  # 畫布圖層排版與「放置」AI 融合測試
    └── mocks.ts                                # Mock 數據與輔助工具
```

---

## Constitution Check

| 憲章條款 | 評估狀態 | 實作保證與對齊依據 |
| :--- | :--- | :--- |
| **第一條 隱私三層** | ✅ PASS | 生成描述僅包含外觀視覺 Prompt，全無使用者個人對話、程式碼或 Satir 冰山 L1 資料。 |
| **第二條 心理機制不變式** | ✅ PASS | 嚴格落實：<br>1. [RISK-04] 抽獎為 L1 即時慶祝；<br>2. [RISK-07] 抽挑戰絕不包含 XP 質押選項；<br>3. [RISK-09] 焦慮隱性狀態下完全禁止主動促銷；<br>4. [R09 §3.3] 60 分鐘滑動視窗最多 5 次防沉迷。 |
| **第三條 規格即合約** | ✅ PASS | 實作內容與澄清後的 `specs/001-m3-11-gacha-ui/spec.md` 百分之百對齊。 |
| **第四條 測試先行** | ✅ PASS | 先撰寫 Vitest 驗收測試（Red），再逐步實作組件使測試轉綠（Green）。 |
| **第五條 MVP 獨立與進階守門** | ⚠️ JUSTIFIED | 模組為獨立前端組件庫，提供完備 Mock 與 2D 降級雙軌模式，不破壞 MVP 本地核心閉環。 |
| **第六條 研究引用** | ✅ PASS | 程式碼與規格均註記 `[R01: DDA 與 PCG]`、`[R08: IKEA 效應 §VI.1]` 與 `[R09: 病態使用風險 §3.3]`。 |
| **第七條 可觀測性** | ✅ PASS | 抽獎、生成與「放置」融合事件均發送遙測至 `raw_tracking_logs`。 |
